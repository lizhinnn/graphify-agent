import uvicorn
import subprocess
import os
import signal
import time


def run_frontend():
    """启动前端服务"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "web")
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=frontend_dir,
        shell=True
    )
    return process


def run_backend():
    """启动后端服务"""
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True, timeout_keep_alive=120)


if __name__ == "__main__":
    print("Starting Graphify Agent services...")
    
    # 启动前端服务
    frontend_process = run_frontend()
    print("Frontend service started. Access at http://localhost:3001")
    
    # 等待前端服务启动
    time.sleep(2)
    
    try:
        # 启动后端服务
        print("Starting backend service...")
        run_backend()
    except KeyboardInterrupt:
        print("\nShutting down services...")
        # 关闭前端服务
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait()
        print("All services have been shut down.")
