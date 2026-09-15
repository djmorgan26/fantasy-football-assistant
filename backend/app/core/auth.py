from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.core.config import settings
from app.db.database import get_database
from app.models.user import User
from app.services.google_oauth import verify_google_id_token, GoogleTokenError

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token authentication. auto_error=False so a missing Authorization
# header reaches get_current_user and returns 401 (not HTTPBearer's 403);
# the frontend interceptor only treats 401 as "logged out".
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def normalize_email(email: str) -> str:
    """Lowercased and trimmed, which is the only form we ever store or match on.

    Addresses are case-insensitive in practice, and Google always hands us the
    lowercase form. Without this, someone who registered as "Dave@Gmail.com"
    and then signs in with Google gets a brand new empty account instead of
    their own, with their leagues stranded on the original row.
    """
    return (email or "").strip().lower()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    # Compare on lower(email) rather than the raw column so rows written
    # before normalization existed still match.
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalize_email(email))
    )
    return result.scalar_one_or_none()


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if user.hashed_password is None:
        # A Google-only account. passlib raises on a None hash, so this has to
        # be caught before verify_password, not inside it.
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession, 
    email: str, 
    password: str, 
    full_name: Optional[str] = None
) -> User:
    hashed_password = get_password_hash(password)
    
    user = User(
        email=normalize_email(email),
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    fantasy_session: Optional[str] = Header(default=None, alias="X-Fantasy-Session"),
    db: AsyncSession = Depends(get_database)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Some proxy/rewrite combinations drop the standard Authorization header
    # on Yahoo's nested routes. The app sends this equivalent bearer token only
    # for those routes; it is verified exactly as an Authorization bearer token
    # and never persisted or logged.
    token = credentials.credentials if credentials else fantasy_session
    if not token:
        raise credentials_exception

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # JWT subject is serialized as a string; the users.id column is an integer.
    # SQLite coerces this automatically but Postgres does not, so cast explicitly.
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class AuthService:
    def __init__(self):
        self.pwd_context = pwd_context

    def _session_for(self, user: User) -> dict:
        """The token + user payload every sign-in path returns."""
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
            },
        }

    
    async def register_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> dict:
        # Check if user already exists
        existing_user = await get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = await create_user(db, email, password, full_name)
        
        # Create access token
        return self._session_for(user)
    
    async def login_user(self, db: AsyncSession, email: str, password: str) -> dict:
        # Look the account up first so we can tell a Google-only user to use
        # the Google button instead of leaving them guessing at a password
        # that does not exist. This does confirm the address is registered,
        # which the generic message below deliberately does not. That is a
        # real trade: it is a small account-enumeration hint, paid for a user
        # who would otherwise be permanently stuck on the login screen.
        existing = await get_user_by_email(db, email)
        if existing is not None and existing.hashed_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account signs in with Google. Use the Google button above.",
            )

        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return self._session_for(user)
    
    async def update_user_profile(
        self,
        db: AsyncSession,
        user_id: int,
        full_name: Optional[str] = None,
        current_password: Optional[str] = None,
        new_password: Optional[str] = None
    ) -> User:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update full name if provided
        if full_name is not None:
            user.full_name = full_name
        
        # Update password if provided.
        #
        # A user who signed up through Google has no password at all. They are
        # already authenticated by their bearer token to be here, so let them
        # set a first one without proving a current password they never had.
        # This is also their only recovery path: without it, losing access to
        # the Google account would mean losing the leagues attached to this
        # one.
        if new_password and user.hashed_password is None:
            user.hashed_password = get_password_hash(new_password)
        elif new_password and current_password:
            if not verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            user.hashed_password = get_password_hash(new_password)
        
        await db.commit()
        await db.refresh(user)
        return user


    async def login_with_google(self, db: AsyncSession, credential: str) -> dict:
        """Verify a Google credential, then link, create or resume an account.

        Three cases, in priority order:

        1. We already know this Google `sub`. Sign that user in.
        2. We do not, but an account exists with the same email. Link them:
           this is what attaches an existing password account to Google the
           first time its owner uses the button, so nobody ends up with two
           accounts and half their leagues on each.
        3. Neither. Create a passwordless account.

        Cases 2 and 3 both require `email_verified`. That check is the whole
        security of this endpoint: without it, anyone who can make Google issue
        a token for an address they do not own (Workspace domains can set
        arbitrary unverified addresses) could claim the matching account here.
        """
        try:
            claims = await verify_google_id_token(credential)
        except GoogleTokenError as exc:
            logger.warning("google_signin_rejected", reason=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google sign-in failed. Please try again.",
            )

        google_sub = claims["sub"]
        email = normalize_email(claims["email"])
        # Google sends this as a real bool, but has historically sent the
        # string "true" as well.
        email_verified = claims.get("email_verified") in (True, "true")
        outcome = "signed_in"

        user = await get_user_by_google_sub(db, google_sub)

        if user is None:
            if not email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your Google account has no verified email address.",
                )

            user = await get_user_by_email(db, email)
            if user is not None:
                user.google_sub = google_sub
                outcome = "linked"
            else:
                user = User(
                    email=email,
                    hashed_password=None,
                    full_name=claims.get("name"),
                    google_sub=google_sub,
                    is_active=True,
                )
                db.add(user)
                outcome = "created"

        # Refresh the picture every time, since Google owns it and we have no
        # other source. Only fill in a name we are missing: if the user has
        # edited theirs here, Google's should not overwrite it on every login.
        if claims.get("picture"):
            user.avatar_url = claims["picture"]
        if not user.full_name and claims.get("name"):
            user.full_name = claims["name"]

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        await db.commit()
        await db.refresh(user)

        logger.info(
            "google_signin", outcome=outcome, user_id=user.id, linked=outcome == "linked"
        )

        session = self._session_for(user)
        session["outcome"] = outcome
        return session


auth_service = AuthService()
