from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserProfile
from models.recruiter import RecruiterProfile
from schemas.user_schemas import UserRegister, UserLogin, Token
from services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user or recruiter."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate role
    if user_data.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum limit of 5 admin accounts reached"
            )
    elif user_data.role not in ["user", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user', 'recruiter', or 'admin'"
        )

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create empty profile
    profile = UserProfile(user_id=new_user.id)
    db.add(profile)

    # If recruiter, create recruiter profile
    if user_data.role == "recruiter":
        recruiter_profile = RecruiterProfile(
            user_id=new_user.id,
            company_name="My Company"  # Default, to be updated
        )
        db.add(recruiter_profile)

    db.commit()

    # Generate token
    token = create_access_token({"user_id": new_user.id, "role": new_user.role})

    return Token(
        access_token=token,
        user_id=new_user.id,
        role=new_user.role,
    )


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact admin.",
        )

    token = create_access_token({"user_id": user.id, "role": user.role})

    return Token(
        access_token=token,
        user_id=user.id,
        role=user.role,
    )


@router.post("/logout")
def logout():
    """Logout (client-side token removal)."""
    return {"message": "Logged out successfully. Please remove the token from client."}
