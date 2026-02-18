from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User, UserProfile
from models.social import Post, Comment, Like, Share, Follow
from schemas.social_schemas import PostCreate, PostResponse, CommentCreate, CommentResponse, FollowResponse, FollowStatsResponse
from utils.dependencies import get_current_user
from services.notification_service import create_notification

router = APIRouter(prefix="/social", tags=["Social"])


def _build_post_response(post, db, current_user_id):
    profile = db.query(UserProfile).filter(UserProfile.user_id == post.user_id).first()
    user = db.query(User).filter(User.id == post.user_id).first()
    return PostResponse(
        id=post.id, user_id=post.user_id, content=post.content,
        media_url=post.media_url, created_at=post.created_at,
        author_name=profile.full_name if profile else (user.email if user else "Unknown"),
        likes_count=db.query(Like).filter(Like.post_id == post.id).count(),
        comments_count=db.query(Comment).filter(Comment.post_id == post.id).count(),
        shares_count=db.query(Share).filter(Share.post_id == post.id).count(),
        is_liked=db.query(Like).filter(Like.post_id == post.id, Like.user_id == current_user_id).first() is not None,
    )


@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(post_data: PostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = Post(user_id=current_user.id, content=post_data.content, media_url=post_data.media_url)
    db.add(post); db.commit(); db.refresh(post)
    return _build_post_response(post, db, current_user.id)


@router.get("/posts", response_model=List[PostResponse])
def get_feed(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
             current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    following_ids = [f.following_id for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()]
    following_ids.append(current_user.id)
    posts = db.query(Post).filter(Post.user_id.in_(following_ids)).order_by(
        Post.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return [_build_post_response(p, db, current_user.id) for p in posts]


@router.get("/posts/explore", response_model=List[PostResponse])
def explore_posts(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                  current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return [_build_post_response(p, db, current_user.id) for p in posts]


@router.post("/posts/{post_id}/comment", response_model=CommentResponse)
def add_comment(post_id: int, comment_data: CommentCreate,
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(post_id=post_id, user_id=current_user.id, content=comment_data.content)
    db.add(comment); db.commit(); db.refresh(comment)
    if post.user_id != current_user.id:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        create_notification(db, post.user_id, "new_comment", "New Comment",
            f"{profile.full_name if profile else current_user.email} commented on your post",
            reference_id=post_id, reference_type="post")
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    return CommentResponse(id=comment.id, post_id=comment.post_id, user_id=comment.user_id,
        content=comment.content, created_at=comment.created_at,
        author_name=profile.full_name if profile else current_user.email)


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()
    result = []
    for c in comments:
        profile = db.query(UserProfile).filter(UserProfile.user_id == c.user_id).first()
        user = db.query(User).filter(User.id == c.user_id).first()
        result.append(CommentResponse(id=c.id, post_id=c.post_id, user_id=c.user_id,
            content=c.content, created_at=c.created_at,
            author_name=profile.full_name if profile else (user.email if user else "Unknown")))
    return result


@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first()
    if existing:
        db.delete(existing); db.commit()
        return {"message": "Post unliked", "liked": False}
    like = Like(post_id=post_id, user_id=current_user.id)
    db.add(like); db.commit()
    if post.user_id != current_user.id:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        create_notification(db, post.user_id, "new_like", "New Like",
            f"{profile.full_name if profile else current_user.email} liked your post",
            reference_id=post_id, reference_type="post")
    return {"message": "Post liked", "liked": True}


@router.post("/posts/{post_id}/share")
def share_post(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    share = Share(post_id=post_id, user_id=current_user.id)
    db.add(share); db.commit()
    if post.user_id != current_user.id:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        create_notification(db, post.user_id, "new_share", "Post Shared",
            f"{profile.full_name if profile else current_user.email} shared your post",
            reference_id=post_id, reference_type="post")
    return {"message": "Post shared successfully"}


@router.post("/users/{user_id}/follow")
def toggle_follow(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id: raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = db.query(User).filter(User.id == user_id).first()
    if not target: raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.following_id == user_id).first()
    if existing:
        db.delete(existing); db.commit()
        return {"message": "Unfollowed", "following": False}
    follow = Follow(follower_id=current_user.id, following_id=user_id)
    db.add(follow); db.commit()
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    create_notification(db, user_id, "new_follower", "New Follower",
        f"{profile.full_name if profile else current_user.email} started following you",
        reference_id=current_user.id, reference_type="user")
    return {"message": "Following", "following": True}


@router.get("/users/{user_id}/followers", response_model=List[FollowResponse])
def get_followers(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    follows = db.query(Follow).filter(Follow.following_id == user_id).all()
    result = []
    for f in follows:
        user = db.query(User).filter(User.id == f.follower_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == f.follower_id).first()
        if user:
            result.append(FollowResponse(id=f.id, user_id=user.id,
                full_name=profile.full_name if profile else None, email=user.email))
    return result


@router.get("/users/{user_id}/following", response_model=List[FollowResponse])
def get_following(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    follows = db.query(Follow).filter(Follow.follower_id == user_id).all()
    result = []
    for f in follows:
        user = db.query(User).filter(User.id == f.following_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == f.following_id).first()
        if user:
            result.append(FollowResponse(id=f.id, user_id=user.id,
                full_name=profile.full_name if profile else None, email=user.email))
    return result


@router.get("/users/{user_id}/follow-stats", response_model=FollowStatsResponse)
def get_follow_stats(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FollowStatsResponse(
        followers_count=db.query(Follow).filter(Follow.following_id == user_id).count(),
        following_count=db.query(Follow).filter(Follow.follower_id == user_id).count(),
        is_following=db.query(Follow).filter(
            Follow.follower_id == current_user.id, Follow.following_id == user_id).first() is not None,
    )
