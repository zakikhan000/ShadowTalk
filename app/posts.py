from fastapi import APIRouter, HTTPException
from app.database import database

post_router = APIRouter()

# 📌 Get All Posts
@post_router.get("/posts")
async def get_all_posts():
    query = "SELECT * FROM Posts WHERE is_deleted = 0"
    posts = await database.fetch_all(query=query)
    return {"posts": posts}

# 📌 Get Post by ID
@post_router.get("/posts/{post_id}")
async def get_post(post_id: int):
    query = "SELECT * FROM Posts WHERE post_id = :post_id AND is_deleted = 0"
    post = await database.fetch_one(query=query, values={"post_id": post_id})

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

# 📌 Create Post
@post_router.post("/posts")
async def create_post(user_id: int, content: str, image_url: str = None):
    query = """
        INSERT INTO Posts (user_id, content, image_url, created_at, updated_at, is_deleted)
        VALUES (:user_id, :content, :image_url, GETDATE(), GETDATE(), 0)
    """
    await database.execute(query=query, values={"user_id": user_id, "content": content, "image_url": image_url})
    return {"message": "Post created successfully"}

# 📌 Update Post
@post_router.put("/posts/{post_id}")
async def update_post(post_id: int, content: str = None, image_url: str = None):
    query = """
        UPDATE Posts 
        SET content = ISNULL(:content, content), image_url = ISNULL(:image_url, image_url), updated_at = GETDATE()
        WHERE post_id = :post_id
    """
    await database.execute(query=query, values={"content": content, "image_url": image_url, "post_id": post_id})
    return {"message": "Post updated successfully"}

# 📌 Soft Delete Post
@post_router.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    query = "UPDATE Posts SET is_deleted = 1 WHERE post_id = :post_id"
    await database.execute(query=query, values={"post_id": post_id})
    return {"message": "Post deleted successfully"}
