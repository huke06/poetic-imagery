"""本地开发启动入口：python run.py"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        # 排除数据/索引文件：否则启动时向量索引构建写入 chroma_data、数据库回补写入 *.db
        # 会被 WatchFiles 捕获并触发热重载，导致构建被反复打断（reload 死循环）
        reload_excludes=["chroma_data/*", "*.db", "*.sqlite3"],
    )
