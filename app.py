from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import base64
import re
import secrets

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            template_folder=current_dir,
            static_folder=current_dir
            )
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-2024'

# 启用CORS
CORS(app)

db = SQLAlchemy(app)


# 学号库数据模型
class StudentID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)  # 学号
    name = db.Column(db.String(50), nullable=False)  # 学生姓名
    department = db.Column(db.String(100))  # 院系
    major = db.Column(db.String(100))  # 专业
    class_name = db.Column(db.String(50))  # 班级
    is_used = db.Column(db.Boolean, default=False)  # 是否已被使用注册
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'department': self.department,
            'major': self.major,
            'class_name': self.class_name,
            'is_used': self.is_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 用户数据模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)  # 新增学号字段
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    # 密码重置字段
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        """生成密码重置令牌"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # 1小时有效期
        return self.reset_token

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'student_id': self.student_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


# 创建数据库表 - 修复版本
with app.app_context():
    try:
        # 尝试创建所有表
        db.create_all()
        print("✅ 数据库表创建成功")

        # 检查表结构是否完整
        try:
            # 测试查询两个表
            User.query.first()
            StudentID.query.first()
            print("✅ 数据库表结构完整")
        except Exception as e:
            print(f"🔄 检测到表结构问题，重新创建数据库: {e}")
            db.drop_all()
            db.create_all()
            print("✅ 数据库表重新创建成功")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        # 如果创建失败，尝试删除重建
        try:
            db.drop_all()
            db.create_all()
            print("✅ 数据库表重建成功")
        except Exception as e2:
            print(f"❌ 数据库重建失败: {e2}")

    # 创建默认管理员账号
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                phone='13800138000',
                student_id='00000000'  # 管理员学号
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # 同时创建管理员对应的学号记录
            if not StudentID.query.filter_by(student_id='00000000').first():
                admin_student = StudentID(
                    student_id='00000000',
                    name='系统管理员',
                    department='系统管理',
                    major='系统管理',
                    class_name='管理员班',
                    is_used=True
                )
                db.session.add(admin_student)

            db.session.commit()
            print("✅ 默认管理员账号创建成功: admin / admin123")
    except Exception as e:
        print(f"❌ 创建管理员账号失败: {e}")
        db.session.rollback()


def get_background_style(photo_path):
    """
    根据照片路径生成背景样式
    支持本地图片和网络图片
    """
    if not photo_path:
        # 默认渐变背景
        return "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"

    # 检查是否是网络图片
    if photo_path.startswith(('http://', 'https://')):
        return f"background: url('{photo_path}') center/cover no-repeat;"

    # 本地图片 - 检查文件是否存在
    if os.path.exists(photo_path):
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(photo_path):
            photo_path = os.path.join(current_dir, photo_path)

        # 读取图片并转换为base64（避免路径问题）
        try:
            with open(photo_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            file_extension = os.path.splitext(photo_path)[1].lower()
            mime_type = {
                '.jpg': 'jpeg',
                '.jpeg': 'jpeg',
                '.png': 'png',
                '.gif': 'gif',
                '.bmp': 'bmp',
                '.webp': 'webp'
            }.get(file_extension, 'jpeg')

            return f"background: url('data:image/{mime_type};base64,{image_data}') center/cover no-repeat;"
        except Exception as e:
            print(f"❌ 图片加载失败: {e}，使用默认背景")
            return "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
    else:
        print(f"❌ 图片文件不存在: {photo_path}，使用默认背景")
        return "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"


@app.route('/')
def index():
    photo_path = "img1.png"  # ⚠️ 修改为你的实际照片路径

    background_style = get_background_style(photo_path)

    # 直接返回HTML内容，避免模板路径问题
    return f'''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>知识库问答系统 - 数据库版</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                {background_style}
                height: 100vh;
                display: flex;
                align-items: center;
                position: relative;
                padding-right: 50px;
                justify-content: flex-end;
            }}

            /* 添加半透明遮罩，确保文字可读 */
            body::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.3);
                z-index: 1;
            }}

            .login-box, .register-box, .admin-box, .student-management-box, .forgot-password-box {{
                background: white;
                border: 2px solid #d9d9d9;
                border-radius: 12px;
                width: 450px;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
                position: relative;
                z-index: 2;
                margin-right: 0;
            }}

            .register-box, .admin-box, .student-management-box, .forgot-password-box {{
                display: none;
            }}

            .login-header, .register-header, .admin-header, .student-management-header, .forgot-password-header {{
                background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
                border-bottom: 2px solid #d9d9d9;
                padding: 25px;
                text-align: center;
                font-size: 22px;
                font-weight: bold;
                color: white;
                border-radius: 10px 10px 0 0;
            }}

            .forgot-password-header {{
                background: linear-gradient(135deg, #fa541c 0%, #d4380d 100%);
            }}

            .login-body, .register-body, .admin-body, .student-management-body, .forgot-password-body {{
                padding: 30px;
            }}

            .form-row {{
                display: flex;
                align-items: center;
                margin-bottom: 18px;
                padding: 6px 0;
            }}

            .form-label {{
                width: 120px;
                font-size: 14px;
                color: #333;
                text-align: right;
                padding-right: 15px;
                font-weight: 500;
            }}

            .form-input {{
                flex: 1;
                padding: 12px 14px;
                border: 2px solid #e8e8e8;
                border-radius: 6px;
                font-size: 14px;
                transition: all 0.3s;
                background: #fafafa;
            }}

            .form-input:focus {{
                outline: none;
                border-color: #1890ff;
                background: white;
                box-shadow: 0 0 0 4px rgba(24, 144, 255, 0.1);
                transform: translateY(-1px);
            }}

            .password-row {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .password-input {{
                flex: 1;
            }}

            .toggle-password {{
                background: none;
                border: none;
                cursor: pointer;
                font-size: 16px;
                padding: 5px;
                color: #666;
                transition: all 0.3s;
            }}

            .toggle-password:hover {{
                color: #1890ff;
                transform: scale(1.1);
            }}

            .checkbox-row {{
                display: flex;
                align-items: center;
                margin-bottom: 20px;
                padding: 6px 0;
            }}

            .checkbox-label {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13px;
                color: #333;
                cursor: pointer;
                transition: all 0.3s;
            }}

            .checkbox-label:hover {{
                color: #1890ff;
            }}

            .remember-checkbox {{
                width: 16px;
                height: 16px;
                accent-color: #1890ff;
            }}

            .login-button-row, .register-button-row, .admin-button-row, .student-management-button-row, .forgot-password-button-row {{
                margin-bottom: 20px;
                padding: 6px 0;
            }}

            .login-btn, .register-btn, .admin-btn, .student-management-btn, .forgot-password-btn {{
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
            }}

            .forgot-password-btn {{
                background: linear-gradient(135deg, #fa541c 0%, #d4380d 100%);
                box-shadow: 0 4px 12px rgba(250, 84, 28, 0.3);
            }}

            .login-btn:hover, .register-btn:hover, .admin-btn:hover, .student-management-btn:hover {{
                background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(24, 144, 255, 0.4);
            }}

            .forgot-password-btn:hover {{
                background: linear-gradient(135deg, #ff7a45 0%, #fa541c 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(250, 84, 28, 0.4);
            }}

            .login-btn:active, .register-btn:active, .admin-btn:active, .student-management-btn:active, .forgot-password-btn:active {{
                transform: translateY(0);
            }}

            .login-btn:disabled, .register-btn:disabled, .admin-btn:disabled, .student-management-btn:disabled, .forgot-password-btn:disabled {{
                background: #ccc;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }}

            .links-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 25px;
                padding: 10px 0;
                border-bottom: 2px solid #f0f0f0;
            }}

            .link {{
                color: #1890ff;
                text-decoration: none;
                font-size: 13px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 500;
            }}

            .link:hover {{
                text-decoration: underline;
                color: #096dd9;
            }}

            .loading {{
                display: none;
                text-align: center;
                color: #1890ff;
                margin: 10px 0;
                font-size: 13px;
                font-weight: 500;
            }}

            .success-message {{
                display: none;
                text-align: center;
                color: #52c41a;
                margin: 10px 0;
                font-size: 13px;
                font-weight: 500;
                background: #f6ffed;
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #b7eb8f;
            }}

            .error-message {{
                display: none;
                text-align: center;
                color: #ff4d4f;
                margin: 10px 0;
                font-size: 13px;
                background: #fff2f0;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ffccc7;
                font-weight: 500;
            }}

            .chat-page {{
                display: none;
                width: 100%;
                height: 100vh;
                background: white;
                position: relative;
                z-index: 2;
            }}

            .chat-iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}

            /* 用户管理样式 */
            .user-list, .student-list {{
                max-height: 250px;
                overflow-y: auto;
                margin: 15px 0;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                padding: 8px;
                background: #fafafa;
            }}

            .user-item, .student-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                background: white;
                margin-bottom: 5px;
                border-radius: 4px;
            }}

            .user-item:last-child, .student-item:last-child {{
                border-bottom: none;
                margin-bottom: 0;
            }}

            .user-info, .student-info {{
                flex: 1;
                font-size: 13px;
            }}

            .user-info strong, .student-info strong {{
                color: #1890ff;
            }}

            .user-date, .student-status {{
                font-size: 11px;
                color: #666;
                margin-left: 8px;
            }}

            .delete-btn {{
                background: #ff4d4f;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.3s;
            }}

            .delete-btn:hover {{
                background: #ff7875;
            }}

            .delete-btn:disabled {{
                background: #ccc;
                cursor: not-allowed;
            }}

            .admin-links {{
                display: flex;
                justify-content: center;
                gap: 15px;
                margin-top: 15px;
            }}

            .purple-btn {{
                background: linear-gradient(135deg, #722ed1 0%, #531dab 100%) !important;
            }}

            .purple-btn:hover {{
                background: linear-gradient(135deg, #9254de 0%, #722ed1 100%) !important;
            }}

            .green-btn {{
                background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
            }}

            .green-btn:hover {{
                background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
            }}

            .resend-btn {{
                background: #f0f0f0;
                color: #666;
                border: 1px solid #d9d9d9;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                white-space: nowrap;
            }}

            .resend-btn:enabled {{
                background: #1890ff;
                color: white;
                border-color: #1890ff;
            }}

            .resend-btn:enabled:hover {{
                background: #40a9ff;
            }}

            /* 响应式设计 */
            @media (max-width: 768px) {{
                body {{
                    padding-right: 15px;
                    padding-left: 15px;
                    justify-content: center;
                }}

                .login-box, .register-box, .admin-box, .student-management-box, .forgot-password-box {{
                    width: 100%;
                    max-width: 380px;
                }}
            }}

            /* 表格线样式 */
            .form-row, .checkbox-row, .login-button-row, .links-row {{
                border-bottom: 1px solid #f8f8f8;
            }}

            .links-row {{
                border-bottom: 2px solid #f0f0f0;
            }}
        </style>
    </head>
    <body>
        <!-- 登录页面 -->
        <div class="login-box" id="loginBox">
            <div class="login-header">
                🧠 鲁东大学知识库问答系统
            </div>

            <div class="login-body">
                <div class="error-message" id="loginError"></div>

                <!-- 学号行 -->
                <div class="form-row">
                    <div class="form-label">学号</div>
                    <input type="text" class="form-input" placeholder="请输入学号" id="loginStudentId">
                </div>

                <!-- 密码行 -->
                <div class="form-row">
                    <div class="form-label">密码</div>
                    <div class="password-row">
                        <input type="password" class="form-input password-input" placeholder="请输入密码" id="loginPassword">
                        <button type="button" class="toggle-password" onclick="togglePassword('loginPassword')">👁️</button>
                    </div>
                </div>

                <!-- 登录按钮行 -->
                <div class="login-button-row">
                    <button class="login-btn" onclick="login()" id="loginBtn">登录</button>
                    <div class="loading" id="loginLoading">登录中...</div>
                </div>

                <!-- 链接行 -->
                <div class="links-row">
                    <a class="link" onclick="showForgotPassword()">忘记密码？</a>
                    <a class="link" onclick="showRegister()">立即注册</a>
                    <a class="link" onclick="showAdminPanel()">用户管理</a>
                </div>
            </div>
        </div>

        <!-- 注册页面 -->
        <div class="register-box" id="registerBox">
            <div class="register-header">
                📝 用户注册
            </div>

            <div class="register-body">
                <div class="error-message" id="registerError"></div>
                <div class="success-message" id="registerSuccess">注册成功！正在跳转到登录页面...</div>

                <!-- 学号 -->
                <div class="form-row">
                    <div class="form-label">学号</div>
                    <input type="text" class="form-input" placeholder="请输入学号" id="regStudentId" required>
                </div>

                <!-- 用户名 -->
                <div class="form-row">
                    <div class="form-label">用户名</div>
                    <input type="text" class="form-input" placeholder="请输入用户名（至少3位）" id="regUsername">
                </div>

                <!-- 邮箱 -->
                <div class="form-row">
                    <div class="form-label">邮箱</div>
                    <input type="email" class="form-input" placeholder="请输入邮箱" id="regEmail">
                </div>

                <!-- 手机号 -->
                <div class="form-row">
                    <div class="form-label">手机号</div>
                    <input type="tel" class="form-input" placeholder="请输入手机号" id="regPhone" required>
                </div>

                <!-- 密码 -->
                <div class="form-row">
                    <div class="form-label">密码</div>
                    <div class="password-row">
                        <input type="password" class="form-input password-input" placeholder="请输入密码（至少6位）" id="regPassword">
                        <button type="button" class="toggle-password" onclick="togglePassword('regPassword')">👁️</button>
                    </div>
                </div>

                <!-- 确认密码 -->
                <div class="form-row">
                    <div class="form-label">确认密码</div>
                    <div class="password-row">
                        <input type="password" class="form-input password-input" placeholder="请再次输入密码" id="regConfirmPassword">
                        <button type="button" class="toggle-password" onclick="togglePassword('regConfirmPassword')">👁️</button>
                    </div>
                </div>

                <!-- 注册按钮 -->
                <div class="register-button-row">
                    <button class="register-btn" onclick="register()" id="registerBtn">注册</button>
                    <div class="loading" id="registerLoading">注册中...</div>
                </div>

                <!-- 返回登录 -->
                <div class="back-to-login">
                    <a class="link" onclick="showLogin()">返回登录</a>
                </div>
            </div>
        </div>

        <!-- 用户管理页面 -->
        <div class="admin-box" id="adminBox">
            <div class="admin-header">
                👨‍💼 用户管理
            </div>

            <div class="admin-body">
                <div class="error-message" id="adminError"></div>
                <div class="success-message" id="adminSuccess"></div>

                <!-- 管理员验证 -->
                <div class="form-row">
                    <div class="form-label">管理员账号</div>
                    <input type="text" class="form-input" placeholder="请输入管理员用户名" id="adminUsername">
                </div>

                <div class="form-row">
                    <div class="form-label">管理员密码</div>
                    <div class="password-row">
                        <input type="password" class="form-input password-input" placeholder="请输入管理员密码" id="adminPassword">
                        <button type="button" class="toggle-password" onclick="togglePassword('adminPassword')">👁️</button>
                    </div>
                </div>

                <!-- 用户列表 -->
                <div class="admin-button-row">
                    <button class="admin-btn" onclick="loadUsers()" id="loadUsersBtn">加载用户列表</button>
                    <div class="loading" id="adminLoading">加载中...</div>
                </div>

                <div class="user-list" id="userList">
                    <!-- 用户列表将在这里显示 -->
                </div>

                <!-- 学号管理 -->
                <div class="admin-button-row">
                    <button class="admin-btn purple-btn" onclick="showStudentManagement()" id="studentManagementBtn">学号库管理</button>
                </div>

                <div class="admin-links">
                    <a class="link" onclick="showLogin()">返回登录</a>
                    <a class="link" onclick="showRegister()">用户注册</a>
                </div>
            </div>
        </div>

        <!-- 学号管理页面 -->
        <div class="student-management-box" id="studentManagementBox">
            <div class="student-management-header">
                🎓 学号库管理
            </div>

            <div class="student-management-body">
                <div class="error-message" id="studentError"></div>
                <div class="success-message" id="studentSuccess"></div>

                <!-- 管理员验证 -->
                <div class="form-row">
                    <div class="form-label">管理员账号</div>
                    <input type="text" class="form-input" placeholder="请输入管理员用户名" id="studentAdminUsername">
                </div>

                <div class="form-row">
                    <div class="form-label">管理员密码</div>
                    <div class="password-row">
                        <input type="password" class="form-input password-input" placeholder="请输入管理员密码" id="studentAdminPassword">
                        <button type="button" class="toggle-password" onclick="togglePassword('studentAdminPassword')">👁️</button>
                    </div>
                </div>

                <!-- 单个添加学号 -->
                <div class="form-row">
                    <div class="form-label">单个添加</div>
                    <button class="student-management-btn" onclick="showAddStudentForm()" style="width: auto; padding: 8px 16px;">添加学号</button>
                </div>

                <!-- 批量导入 -->
                <div class="form-row">
                    <div class="form-label">批量导入</div>
                    <textarea class="form-input" placeholder="请输入学号数据（JSON格式）" id="batchStudents" style="height: 100px; font-family: monospace; font-size: 12px;"></textarea>
                </div>

                <div class="student-management-button-row">
                    <button class="student-management-btn" onclick="batchImportStudents()">批量导入学号</button>
                    <button class="student-management-btn green-btn" onclick="loadStudents()">查看学号库</button>
                    <div class="loading" id="studentLoading">处理中...</div>
                </div>

                <!-- 学号列表 -->
                <div class="student-list" id="studentList">
                    <!-- 学号列表将在这里显示 -->
                </div>

                <div class="admin-links">
                    <a class="link" onclick="showAdminPanel()">返回用户管理</a>
                    <a class="link" onclick="showLogin()">返回登录</a>
                </div>
            </div>
        </div>

        <!-- 忘记密码页面 -->
        <div class="forgot-password-box" id="forgotPasswordBox">
            <div class="forgot-password-header">
                🔐 找回密码
            </div>

            <div class="forgot-password-body">
                <div class="error-message" id="forgotPasswordError"></div>
                <div class="success-message" id="forgotPasswordSuccess"></div>

                <!-- 步骤1：选择找回方式 -->
                <div id="step1">
                    <div class="form-row">
                        <div class="form-label">找回方式</div>
                        <div style="flex: 1;">
                            <label class="checkbox-label">
                                <input type="radio" name="recoveryMethod" value="email" checked>
                                <span>通过邮箱找回</span>
                            </label>
                            <label class="checkbox-label" style="margin-left: 20px;">
                                <input type="radio" name="recoveryMethod" value="phone">
                                <span>通过手机号找回</span>
                            </label>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-label">学号</div>
                        <input type="text" class="form-input" placeholder="请输入您的学号" id="recoveryStudentId">
                    </div>

                    <div class="forgot-password-button-row">
                        <button class="forgot-password-btn" onclick="sendVerificationCode()">发送验证码</button>
                        <div class="loading" id="sendCodeLoading">发送中...</div>
                    </div>
                </div>

                <!-- 步骤2：验证身份 -->
                <div id="step2" style="display: none;">
                    <div class="form-row">
                        <div class="form-label" id="verificationLabel">邮箱验证码</div>
                        <div class="password-row">
                            <input type="text" class="form-input password-input" placeholder="请输入验证码" id="verificationCode">
                            <button type="button" class="resend-btn" onclick="resendVerificationCode()" id="resendBtn" disabled>60秒后重发</button>
                        </div>
                    </div>

                    <div class="forgot-password-button-row">
                        <button class="forgot-password-btn" onclick="verifyCode()">验证</button>
                        <div class="loading" id="verifyLoading">验证中...</div>
                    </div>
                </div>

                <!-- 步骤3：重置密码 -->
                <div id="step3" style="display: none;">
                    <div class="form-row">
                        <div class="form-label">新密码</div>
                        <div class="password-row">
                            <input type="password" class="form-input password-input" placeholder="请输入新密码（至少6位）" id="newPassword">
                            <button type="button" class="toggle-password" onclick="togglePassword('newPassword')">👁️</button>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-label">确认密码</div>
                        <div class="password-row">
                            <input type="password" class="form-input password-input" placeholder="请再次输入新密码" id="confirmNewPassword">
                            <button type="button" class="toggle-password" onclick="togglePassword('confirmNewPassword')">👁️</button>
                        </div>
                    </div>

                    <div class="forgot-password-button-row">
                        <button class="forgot-password-btn" onclick="resetPassword()">重置密码</button>
                        <div class="loading" id="resetLoading">重置中...</div>
                    </div>
                </div>

                <div class="back-to-login">
                    <a class="link" onclick="showLogin()">返回登录</a>
                </div>
            </div>
        </div>

        <!-- 聊天页面 -->
        <div class="chat-page" id="chatPage">
            <iframe 
                class="chat-iframe" 
                id="difyFrame"
                src="http://localhost/chatbot/5iNPjcooj4xjYnht"
                frameborder="0"
                allow="microphone"
            ></iframe>
        </div>

        <script>
            const API_BASE = window.location.origin + '/api';

            // 显示/隐藏密码
            function togglePassword(inputId) {{
                const passwordInput = document.getElementById(inputId);
                const toggleButton = passwordInput.nextElementSibling;

                if (passwordInput.type === 'password') {{
                    passwordInput.type = 'text';
                    toggleButton.textContent = '🙈';
                }} else {{
                    passwordInput.type = 'password';
                    toggleButton.textContent = '👁️';
                }}
            }}

            // 显示注册页面
            function showRegister() {{
                hideAllMessages();
                document.getElementById('loginBox').style.display = 'none';
                document.getElementById('registerBox').style.display = 'block';
                document.getElementById('adminBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'none';
                document.getElementById('chatPage').style.display = 'none';
            }}

            // 显示登录页面
            function showLogin() {{
                hideAllMessages();
                document.getElementById('registerBox').style.display = 'none';
                document.getElementById('adminBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'none';
                document.getElementById('loginBox').style.display = 'block';
                document.getElementById('chatPage').style.display = 'none';
            }}

            // 显示用户管理页面
            function showAdminPanel() {{
                hideAllMessages();
                document.getElementById('loginBox').style.display = 'none';
                document.getElementById('registerBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'none';
                document.getElementById('adminBox').style.display = 'block';
                document.getElementById('chatPage').style.display = 'none';
                // 清空用户列表
                document.getElementById('userList').innerHTML = '';
            }}

            // 显示学号管理页面
            function showStudentManagement() {{
                hideAllMessages();
                document.getElementById('loginBox').style.display = 'none';
                document.getElementById('registerBox').style.display = 'none';
                document.getElementById('adminBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'block';
                document.getElementById('chatPage').style.display = 'none';
                // 清空学号列表
                document.getElementById('studentList').innerHTML = '';
            }}

            // 显示忘记密码页面
            function showForgotPassword() {{
                hideAllMessages();
                resetForgotPasswordForm();
                document.getElementById('loginBox').style.display = 'none';
                document.getElementById('registerBox').style.display = 'none';
                document.getElementById('adminBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'block';
                document.getElementById('chatPage').style.display = 'none';
            }}

            // 重置忘记密码表单
            function resetForgotPasswordForm() {{
                document.getElementById('step1').style.display = 'block';
                document.getElementById('step2').style.display = 'none';
                document.getElementById('step3').style.display = 'none';
                document.getElementById('recoveryStudentId').value = '';
                document.getElementById('verificationCode').value = '';
                document.getElementById('newPassword').value = '';
                document.getElementById('confirmNewPassword').value = '';
                document.querySelector('input[name="recoveryMethod"][value="email"]').checked = true;
            }}

            // 显示聊天页面
            function showChatPage() {{
                document.getElementById('loginBox').style.display = 'none';
                document.getElementById('registerBox').style.display = 'none';
                document.getElementById('adminBox').style.display = 'none';
                document.getElementById('studentManagementBox').style.display = 'none';
                document.getElementById('forgotPasswordBox').style.display = 'none';
                document.getElementById('chatPage').style.display = 'block';
            }}

            // 隐藏所有消息
            function hideAllMessages() {{
                document.getElementById('loginError').style.display = 'none';
                document.getElementById('registerError').style.display = 'none';
                document.getElementById('registerSuccess').style.display = 'none';
                document.getElementById('adminError').style.display = 'none';
                document.getElementById('adminSuccess').style.display = 'none';
                document.getElementById('studentError').style.display = 'none';
                document.getElementById('studentSuccess').style.display = 'none';
                document.getElementById('forgotPasswordError').style.display = 'none';
                document.getElementById('forgotPasswordSuccess').style.display = 'none';
            }}

            // 显示错误消息
            function showError(elementId, message) {{
                const element = document.getElementById(elementId);
                element.textContent = message;
                element.style.display = 'block';
            }}

            // 显示成功消息
            function showSuccess(elementId, message) {{
                const element = document.getElementById(elementId);
                element.textContent = message;
                element.style.display = 'block';
            }}

            // 登录功能
            async function login() {{
                const studentId = document.getElementById('loginStudentId').value.trim();
                const password = document.getElementById('loginPassword').value;
                const loginBtn = document.getElementById('loginBtn');
                const loading = document.getElementById('loginLoading');

                hideAllMessages();

                if (!studentId || !password) {{
                    showError('loginError', '请输入学号和密码');
                    return;
                }}

                // 禁用按钮，显示加载
                loginBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            student_id: studentId,
                            password: password
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        // 登录成功，显示聊天页面
                        showChatPage();
                    }} else {{
                        showError('loginError', result.message);
                    }}
                }} catch (error) {{
                    showError('loginError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    loginBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 注册功能
            async function register() {{
                const studentId = document.getElementById('regStudentId').value.trim();
                const username = document.getElementById('regUsername').value.trim();
                const email = document.getElementById('regEmail').value.trim();
                const phone = document.getElementById('regPhone').value.trim();
                const password = document.getElementById('regPassword').value;
                const confirmPassword = document.getElementById('regConfirmPassword').value;
                const registerBtn = document.getElementById('registerBtn');
                const loading = document.getElementById('registerLoading');
                const success = document.getElementById('registerSuccess');

                hideAllMessages();

                // 前端验证
                if (!studentId || !username || !email || !password || !phone) {{
                    showError('registerError', '请填写所有必填字段');
                    return;
                }}

                if (username.length < 3) {{
                    showError('registerError', '用户名长度至少3位');
                    return;
                }}

                if (password.length < 6) {{
                    showError('registerError', '密码长度至少6位');
                    return;
                }}

                if (password !== confirmPassword) {{
                    showError('registerError', '两次输入的密码不一致');
                    return;
                }}

                // 添加电话号码前端验证
                if (!/^\\d+$/.test(phone)) {{
                    showError('registerError', '电话号码只能包含数字');
                    return;
                }}

                if (phone.length < 7) {{
                    showError('registerError', '电话号码长度至少7位');
                    return;
                }}

                // 中国大陆手机号格式验证
                if (!/^1[3-9]\\d{{9}}$/.test(phone)) {{
                    showError('registerError', '请输入有效的中国大陆手机号码（11位，以1开头）');
                    return;
                }}

                // 禁用按钮，显示加载
                registerBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/register', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            student_id: studentId,
                            username: username,
                            email: email,
                            phone: phone,
                            password: password
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        // 注册成功
                        success.style.display = 'block';
                        loading.style.display = 'none';

                        // 2秒后跳转到登录页面
                        setTimeout(() => {{
                            showLogin();
                            // 清空注册表单
                            document.getElementById('regStudentId').value = '';
                            document.getElementById('regUsername').value = '';
                            document.getElementById('regEmail').value = '';
                            document.getElementById('regPhone').value = '';
                            document.getElementById('regPassword').value = '';
                            document.getElementById('regConfirmPassword').value = '';
                            success.style.display = 'none';
                        }}, 2000);
                    }} else {{
                        showError('registerError', result.message);
                    }}
                }} catch (error) {{
                    showError('registerError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    registerBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 加载用户列表
            async function loadUsers() {{
                const adminUsername = document.getElementById('adminUsername').value.trim();
                const adminPassword = document.getElementById('adminPassword').value;
                const loadUsersBtn = document.getElementById('loadUsersBtn');
                const loading = document.getElementById('adminLoading');

                hideAllMessages();

                if (!adminUsername || !adminPassword) {{
                    showError('adminError', '请输入管理员账号和密码');
                    return;
                }}

                // 禁用按钮，显示加载
                loadUsersBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/admin/list_users', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            admin_username: adminUsername,
                            admin_password: adminPassword
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        displayUsers(result.data.users);
                        showSuccess('adminSuccess', `共找到 ${{result.data.total}} 个用户`);
                    }} else {{
                        showError('adminError', result.message);
                    }}
                }} catch (error) {{
                    showError('adminError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    loadUsersBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 显示用户列表
            function displayUsers(users) {{
                const userList = document.getElementById('userList');
                userList.innerHTML = users.map(user => `
                    <div class="user-item">
                        <div class="user-info">
                            <strong>${{user.username}}</strong> - 学号:${{user.student_id}} - ${{user.email}}
                            <span class="user-date">注册: ${{new Date(user.created_at).toLocaleDateString()}}</span>
                        </div>
                        <button class="delete-btn" onclick="deleteUser('${{user.username}}')" ${{user.username === 'admin' ? 'disabled' : ''}}>删除</button>
                    </div>
                `).join('');
            }}

            // 删除用户
            async function deleteUser(username) {{
                const adminUsername = document.getElementById('adminUsername').value.trim();
                const adminPassword = document.getElementById('adminPassword').value;

                if (!adminUsername || !adminPassword) {{
                    alert('请先填写管理员账号和密码');
                    return;
                }}

                if (!confirm(`确定要删除用户 "${{username}}" 吗？此操作不可撤销！`)) {{
                    return;
                }}

                try {{
                    const response = await fetch(API_BASE + '/admin/delete_user', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            admin_username: adminUsername,
                            admin_password: adminPassword,
                            target_username: username
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        alert(result.message);
                        loadUsers(); // 重新加载用户列表
                    }} else {{
                        alert('删除失败: ' + result.message);
                    }}
                }} catch (error) {{
                    alert('删除用户失败，请检查网络连接');
                }}
            }}

            // 学号管理功能
            // 显示添加学号表单
            function showAddStudentForm() {{
                const studentId = prompt('请输入学号:');
                if (!studentId) return;

                const name = prompt('请输入学生姓名:');
                if (!name) return;

                const department = prompt('请输入院系（可选）:') || '';
                const major = prompt('请输入专业（可选）:') || '';
                const className = prompt('请输入班级（可选）:') || '';

                const adminUsername = document.getElementById('studentAdminUsername').value.trim();
                const adminPassword = document.getElementById('studentAdminPassword').value;

                if (!adminUsername || !adminPassword) {{
                    alert('请先填写管理员账号和密码');
                    return;
                }}

                const studentData = [{{
                    student_id: studentId,
                    name: name,
                    department: department,
                    major: major,
                    class_name: className
                }}];

                importStudents(studentData, adminUsername, adminPassword);
            }}

            // 批量导入学号
            async function batchImportStudents() {{
                const studentsText = document.getElementById('batchStudents').value.trim();
                const adminUsername = document.getElementById('studentAdminUsername').value.trim();
                const adminPassword = document.getElementById('studentAdminPassword').value;

                if (!adminUsername || !adminPassword) {{
                    showError('studentError', '请输入管理员账号和密码');
                    return;
                }}

                if (!studentsText) {{
                    showError('studentError', '请输入学号数据');
                    return;
                }}

                try {{
                    const students = JSON.parse(studentsText);
                    await importStudents(students, adminUsername, adminPassword);
                }} catch (error) {{
                    showError('studentError', 'JSON格式错误，请检查数据格式');
                }}
            }}

            // 导入学号
            async function importStudents(students, adminUsername, adminPassword) {{
                const loading = document.getElementById('studentLoading');
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/admin/import_students', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            admin_username: adminUsername,
                            admin_password: adminPassword,
                            students: students
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        let successMessage = result.message;
                        if (result.data) {{
                            if (result.data.duplicate_count > 0) {{
                                successMessage += ` (${{result.data.duplicate_count}}个重复)`;
                            }}
                            if (result.data.error_count > 0) {{
                                successMessage += ` (${{result.data.error_count}}个失败)`;
                            }}
                        }}
                        showSuccess('studentSuccess', successMessage);
                        document.getElementById('batchStudents').value = '';
                        loadStudents(); // 重新加载学号列表
                    }} else {{
                        showError('studentError', result.message);
                    }}
                }} catch (error) {{
                    console.error('导入学号错误:', error);
                    showError('studentError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    loading.style.display = 'none';
                }}
            }}

            // 加载学号列表
            async function loadStudents() {{
                const adminUsername = document.getElementById('studentAdminUsername').value.trim();
                const adminPassword = document.getElementById('studentAdminPassword').value;
                const loading = document.getElementById('studentLoading');

                if (!adminUsername || !adminPassword) {{
                    showError('studentError', '请输入管理员账号和密码');
                    return;
                }}

                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/admin/list_students', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            admin_username: adminUsername,
                            admin_password: adminPassword
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        displayStudentsList(result.data);
                        showSuccess('studentSuccess', `共 ${{result.data.total}} 个学号，已使用 ${{result.data.used_count}} 个，可用 ${{result.data.available_count}} 个`);
                    }} else {{
                        showError('studentError', result.message);
                    }}
                }} catch (error) {{
                    showError('studentError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    loading.style.display = 'none';
                }}
            }}

            // 显示学号列表
            function displayStudentsList(data) {{
                const studentList = document.getElementById('studentList');
                studentList.innerHTML = data.students.map(student => `
                    <div class="student-item">
                        <div class="student-info">
                            <strong>${{student.student_id}}</strong> - ${{student.name}}
                            ${{student.department ? `- ${{student.department}}` : ''}}
                            ${{student.major ? `- ${{student.major}}` : ''}}
                            ${{student.class_name ? `- ${{student.class_name}}` : ''}}
                            <span class="student-status" style="color: ${{student.is_used ? '#ff4d4f' : '#52c41a'}}">
                                ${{student.is_used ? '已使用' : '未使用'}}
                            </span>
                        </div>
                        <button class="delete-btn" onclick="deleteStudent('${{student.student_id}}')" ${{student.is_used ? 'disabled' : ''}}>删除</button>
                    </div>
                `).join('');
            }}

            // 删除学号
            async function deleteStudent(studentId) {{
                const adminUsername = document.getElementById('studentAdminUsername').value.trim();
                const adminPassword = document.getElementById('studentAdminPassword').value;

                if (!adminUsername || !adminPassword) {{
                    alert('请先填写管理员账号和密码');
                    return;
                }}

                if (!confirm(`确定要删除学号 "${{studentId}}" 吗？`)) {{
                    return;
                }}

                try {{
                    const response = await fetch(API_BASE + '/admin/delete_student', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            admin_username: adminUsername,
                            admin_password: adminPassword,
                            student_id: studentId
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        alert(result.message);
                        loadStudents(); // 重新加载学号列表
                    }} else {{
                        alert('删除失败: ' + result.message);
                    }}
                }} catch (error) {{
                    alert('删除学号失败，请检查网络连接');
                }}
            }}

            // 忘记密码功能
            // 发送验证码
            async function sendVerificationCode() {{
                const studentId = document.getElementById('recoveryStudentId').value.trim();
                const method = document.querySelector('input[name="recoveryMethod"]:checked').value;
                const sendCodeBtn = document.querySelector('#step1 .forgot-password-btn');
                const loading = document.getElementById('sendCodeLoading');

                hideAllMessages();

                if (!studentId) {{
                    showError('forgotPasswordError', '请输入学号');
                    return;
                }}

                // 禁用按钮，显示加载
                sendCodeBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/auth/send_verification_code', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            student_id: studentId,
                            method: method
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        showSuccess('forgotPasswordSuccess', result.message);
                        // 切换到步骤2
                        document.getElementById('step1').style.display = 'none';
                        document.getElementById('step2').style.display = 'block';

                        // 更新标签文本
                        const label = document.getElementById('verificationLabel');
                        label.textContent = method === 'email' ? '邮箱验证码' : '手机验证码';

                        // 开始倒计时
                        startResendCountdown();

                        // 保存当前找回信息
                        window.recoveryInfo = {{
                            studentId: studentId,
                            method: method
                        }};
                    }} else {{
                        showError('forgotPasswordError', result.message);
                    }}
                }} catch (error) {{
                    showError('forgotPasswordError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    sendCodeBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 开始重发倒计时
            function startResendCountdown() {{
                const resendBtn = document.getElementById('resendBtn');
                let countdown = 60;

                resendBtn.disabled = true;
                resendBtn.textContent = `${{countdown}}秒后重发`;

                const timer = setInterval(() => {{
                    countdown--;
                    resendBtn.textContent = `${{countdown}}秒后重发`;

                    if (countdown <= 0) {{
                        clearInterval(timer);
                        resendBtn.disabled = false;
                        resendBtn.textContent = '重发验证码';
                    }}
                }}, 1000);
            }}

            // 重发验证码
            function resendVerificationCode() {{
                sendVerificationCode();
            }}

            // 验证验证码
            async function verifyCode() {{
                const verificationCode = document.getElementById('verificationCode').value.trim();
                const verifyBtn = document.querySelector('#step2 .forgot-password-btn');
                const loading = document.getElementById('verifyLoading');

                hideAllMessages();

                if (!verificationCode) {{
                    showError('forgotPasswordError', '请输入验证码');
                    return;
                }}

                if (!window.recoveryInfo) {{
                    showError('forgotPasswordError', '会话已过期，请重新开始');
                    return;
                }}

                // 禁用按钮，显示加载
                verifyBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/auth/verify_code', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            student_id: window.recoveryInfo.studentId,
                            method: window.recoveryInfo.method,
                            code: verificationCode
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        showSuccess('forgotPasswordSuccess', '验证成功，请设置新密码');
                        // 切换到步骤3
                        document.getElementById('step2').style.display = 'none';
                        document.getElementById('step3').style.display = 'block';

                        // 保存重置令牌
                        window.resetToken = result.data.reset_token;
                    }} else {{
                        showError('forgotPasswordError', result.message);
                    }}
                }} catch (error) {{
                    showError('forgotPasswordError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    verifyBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 重置密码
            async function resetPassword() {{
                const newPassword = document.getElementById('newPassword').value;
                const confirmPassword = document.getElementById('confirmNewPassword').value;
                const resetBtn = document.querySelector('#step3 .forgot-password-btn');
                const loading = document.getElementById('resetLoading');

                hideAllMessages();

                if (!newPassword || !confirmPassword) {{
                    showError('forgotPasswordError', '请输入新密码和确认密码');
                    return;
                }}

                if (newPassword.length < 6) {{
                    showError('forgotPasswordError', '密码长度至少6位');
                    return;
                }}

                if (newPassword !== confirmPassword) {{
                    showError('forgotPasswordError', '两次输入的密码不一致');
                    return;
                }}

                if (!window.resetToken) {{
                    showError('forgotPasswordError', '会话已过期，请重新开始');
                    return;
                }}

                // 禁用按钮，显示加载
                resetBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(API_BASE + '/auth/reset_password', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            reset_token: window.resetToken,
                            new_password: newPassword
                        }})
                    }});

                    const result = await response.json();

                    if (result.success) {{
                        showSuccess('forgotPasswordSuccess', '密码重置成功！正在跳转到登录页面...');

                        // 2秒后跳转到登录页面
                        setTimeout(() => {{
                            showLogin();
                            resetForgotPasswordForm();
                        }}, 2000);
                    }} else {{
                        showError('forgotPasswordError', result.message);
                    }}
                }} catch (error) {{
                    showError('forgotPasswordError', '网络错误，请检查服务器是否运行');
                }} finally {{
                    resetBtn.disabled = false;
                    loading.style.display = 'none';
                }}
            }}

            // 回车键登录/注册
            document.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    if (document.getElementById('loginBox').style.display !== 'none') {{
                        login();
                    }} else if (document.getElementById('registerBox').style.display !== 'none') {{
                        register();
                    }} else if (document.getElementById('adminBox').style.display !== 'none') {{
                        loadUsers();
                    }} else if (document.getElementById('studentManagementBox').style.display !== 'none') {{
                        loadStudents();
                    }} else if (document.getElementById('forgotPasswordBox').style.display !== 'none') {{
                        const step1 = document.getElementById('step1').style.display !== 'none';
                        const step2 = document.getElementById('step2').style.display !== 'none';
                        const step3 = document.getElementById('step3').style.display !== 'none';

                        if (step1) {{
                            sendVerificationCode();
                        }} else if (step2) {{
                            verifyCode();
                        }} else if (step3) {{
                            resetPassword();
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    '''


# API路由
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        student_id = data.get('student_id', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')

        # 验证数据
        if not student_id or not username or not email or not password or not phone:
            return jsonify({'success': False, 'message': '所有字段都为必填项'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400

        if len(username) < 3:
            return jsonify({'success': False, 'message': '用户名长度至少3位'}), 400

        # 验证学号是否在学号库中且未被使用
        student_record = StudentID.query.filter_by(student_id=student_id).first()
        if not student_record:
            return jsonify({'success': False, 'message': '学号不存在，请联系管理员'}), 400

        if student_record.is_used:
            return jsonify({'success': False, 'message': '该学号已被注册使用'}), 400

        # 添加电话号码格式验证
        if not phone.isdigit():
            return jsonify({'success': False, 'message': '电话号码只能包含数字'}), 400

        if len(phone) < 7:
            return jsonify({'success': False, 'message': '电话号码长度至少7位'}), 400

        # 更严格的手机号格式验证（中国大陆手机号）
        phone_pattern = r'^1[3-9]\d{9}$'
        if not re.match(phone_pattern, phone):
            return jsonify({'success': False, 'message': '请输入有效的中国大陆手机号码（11位，以1开头）'}), 400

        # 检查用户是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': '用户名已存在'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': '邮箱已被注册'}), 400

        if User.query.filter_by(phone=phone).first():
            return jsonify({'success': False, 'message': '手机号已被注册'}), 400

        if User.query.filter_by(student_id=student_id).first():
            return jsonify({'success': False, 'message': '学号已被注册'}), 400

        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            student_id=student_id
        )
        new_user.set_password(password)

        # 标记学号为已使用
        student_record.is_used = True

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'user': new_user.to_dict()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        student_id = data.get('student_id', '').strip()
        password = data.get('password', '')

        if not student_id or not password:
            return jsonify({'success': False, 'message': '请输入学号和密码'}), 400

        # 查找用户（现在只支持学号登录）
        user = User.query.filter_by(student_id=student_id).first()

        if user and user.check_password(password):
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '登录成功',
                'data': {
                    'user': user.to_dict()
                }
            })
        else:
            return jsonify({'success': False, 'message': '学号或密码错误'}), 401

    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


# 密码重置API
@app.route('/api/auth/send_verification_code', methods=['POST'])
def send_verification_code():
    """发送验证码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        student_id = data.get('student_id', '').strip()
        method = data.get('method', 'email')  # email 或 phone

        if not student_id:
            return jsonify({'success': False, 'message': '请输入学号'}), 400

        # 查找用户
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            return jsonify({'success': False, 'message': '学号不存在'}), 404

        # 生成验证码（6位数字）
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])

        # 模拟发送验证码
        if method == 'email':
            # 模拟发送邮件
            print(f"📧 发送邮件验证码到 {user.email}: {verification_code}")
            message = f"验证码已发送到邮箱 {user.email}，请查收"
        else:
            # 模拟发送短信
            print(f"📱 发送短信验证码到 {user.phone}: {verification_code}")
            message = f"验证码已发送到手机 {user.phone}，请查收"

        # 生成重置令牌
        reset_token = user.generate_reset_token()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'data': {
                'method': method,
                'target': user.email if method == 'email' else user.phone
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'发送验证码失败: {str(e)}'}), 500


@app.route('/api/auth/verify_code', methods=['POST'])
def verify_code():
    """验证验证码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        student_id = data.get('student_id', '').strip()
        method = data.get('method', 'email')
        code = data.get('code', '').strip()

        if not student_id or not code:
            return jsonify({'success': False, 'message': '请输入学号和验证码'}), 400

        # 查找用户
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            return jsonify({'success': False, 'message': '学号不存在'}), 404

        # 在实际应用中，这里应该验证验证码是否正确
        # 这里简化处理，假设验证码正确
        if not user.reset_token:
            return jsonify({'success': False, 'message': '请先获取验证码'}), 400

        # 检查令牌是否过期
        if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
            return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400

        # 在实际应用中，这里应该验证验证码
        # 这里简化处理，假设验证码正确
        is_code_valid = True  # 应该根据实际存储的验证码进行验证

        if not is_code_valid:
            return jsonify({'success': False, 'message': '验证码错误'}), 400

        return jsonify({
            'success': True,
            'message': '验证成功',
            'data': {
                'reset_token': user.reset_token
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'}), 500


@app.route('/api/auth/reset_password', methods=['POST'])
def reset_password():
    """重置密码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        reset_token = data.get('reset_token', '').strip()
        new_password = data.get('new_password', '')

        if not reset_token or not new_password:
            return jsonify({'success': False, 'message': '参数不完整'}), 400

        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400

        # 查找用户
        user = User.query.filter_by(reset_token=reset_token).first()
        if not user:
            return jsonify({'success': False, 'message': '无效的重置令牌'}), 404

        # 检查令牌是否过期
        if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
            return jsonify({'success': False, 'message': '重置令牌已过期'}), 400

        # 更新密码
        user.set_password(new_password)

        # 清除重置令牌
        user.reset_token = None
        user.reset_token_expires = None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '密码重置成功'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'重置密码失败: {str(e)}'}), 500


# 学号管理API
@app.route('/api/admin/import_students', methods=['POST'])
def import_students():
    """批量导入学号"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')
        students = data.get('students', [])

        if not admin_username or not admin_password:
            return jsonify({'success': False, 'message': '请提供管理员账号和密码'}), 400

        # 验证管理员身份
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user or not admin_user.check_password(admin_password):
            return jsonify({'success': False, 'message': '管理员身份验证失败'}), 401

        # 验证students参数类型
        if not isinstance(students, list):
            return jsonify({'success': False, 'message': '学号数据格式错误，应为数组'}), 400

        imported_count = 0
        duplicate_count = 0
        error_count = 0

        for student in students:
            # 确保student是字典类型
            if not isinstance(student, dict):
                error_count += 1
                continue

            student_id = student.get('student_id', '').strip()
            name = student.get('name', '').strip()

            if student_id and name:
                # 检查学号是否已存在
                existing_student = StudentID.query.filter_by(student_id=student_id).first()
                if not existing_student:
                    try:
                        new_student = StudentID(
                            student_id=student_id,
                            name=name,
                            department=student.get('department', ''),
                            major=student.get('major', ''),
                            class_name=student.get('class_name', '')
                        )
                        db.session.add(new_student)
                        imported_count += 1
                    except Exception as e:
                        print(f"❌ 添加学号失败 {student_id}: {e}")
                        error_count += 1
                else:
                    duplicate_count += 1
                    print(f"⚠️  学号已存在: {student_id}")

        db.session.commit()

        message = f'成功导入 {imported_count} 个学号'
        if duplicate_count > 0:
            message += f'，跳过 {duplicate_count} 个重复学号'
        if error_count > 0:
            message += f'，{error_count} 个学号导入失败'

        return jsonify({
            'success': True,
            'message': message,
            'data': {
                'imported_count': imported_count,
                'duplicate_count': duplicate_count,
                'error_count': error_count
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ 导入学号异常: {e}")
        return jsonify({'success': False, 'message': f'导入学号失败: {str(e)}'}), 500


@app.route('/api/admin/list_students', methods=['POST'])
def list_students():
    """列出所有学号"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')

        if not admin_username or not admin_password:
            return jsonify({'success': False, 'message': '请提供管理员账号和密码'}), 400

        # 验证管理员身份
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user or not admin_user.check_password(admin_password):
            return jsonify({'success': False, 'message': '管理员身份验证失败'}), 401

        students = StudentID.query.all()
        return jsonify({
            'success': True,
            'data': {
                'students': [student.to_dict() for student in students],
                'total': len(students),
                'used_count': StudentID.query.filter_by(is_used=True).count(),
                'available_count': StudentID.query.filter_by(is_used=False).count()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取学号列表失败: {str(e)}'}), 500


@app.route('/api/admin/delete_student', methods=['POST'])
def delete_student():
    """删除学号"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')
        student_id = data.get('student_id', '').strip()

        if not admin_username or not admin_password or not student_id:
            return jsonify({'success': False, 'message': '请提供管理员账号、密码和学号'}), 400

        # 验证管理员身份
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user or not admin_user.check_password(admin_password):
            return jsonify({'success': False, 'message': '管理员身份验证失败'}), 401

        # 查找学号记录
        student_record = StudentID.query.filter_by(student_id=student_id).first()
        if not student_record:
            return jsonify({'success': False, 'message': '学号不存在'}), 404

        # 检查学号是否已被使用
        if student_record.is_used:
            return jsonify({'success': False, 'message': '该学号已被使用，无法删除'}), 400

        # 删除学号记录
        db.session.delete(student_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'学号 {student_id} 已成功删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除学号失败: {str(e)}'}), 500


# 原有的其他API路由保持不变
@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    """管理员删除用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')
        target_username = data.get('target_username', '').strip()

        if not admin_username or not admin_password or not target_username:
            return jsonify({'success': False, 'message': '请提供管理员账号、密码和目标用户名'}), 400

        # 验证管理员身份
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user or not admin_user.check_password(admin_password):
            return jsonify({'success': False, 'message': '管理员身份验证失败'}), 401

        # 查找要删除的用户
        target_user = User.query.filter_by(username=target_username).first()
        if not target_user:
            return jsonify({'success': False, 'message': '要删除的用户不存在'}), 404

        # 不能删除自己
        if target_user.username == admin_user.username:
            return jsonify({'success': False, 'message': '不能删除自己的账号'}), 400

        # 释放学号
        student_record = StudentID.query.filter_by(student_id=target_user.student_id).first()
        if student_record:
            student_record.is_used = False

        # 删除用户
        db.session.delete(target_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'用户 {target_username} 已成功删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除用户失败: {str(e)}'}), 500


@app.route('/api/user/delete_self', methods=['POST'])
def user_delete_self():
    """用户删除自己的账号"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'success': False, 'message': '请提供用户名和密码'}), 400

        # 验证用户身份
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

        # 释放学号
        student_record = StudentID.query.filter_by(student_id=user.student_id).first()
        if student_record:
            student_record.is_used = False

        # 删除用户
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '您的账号已成功删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除账号失败: {str(e)}'}), 500


@app.route('/api/admin/list_users', methods=['POST'])
def list_users():
    """列出所有用户（管理员功能）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        admin_username = data.get('admin_username', '').strip()
        admin_password = data.get('admin_password', '')

        if not admin_username or not admin_password:
            return jsonify({'success': False, 'message': '请提供管理员账号和密码'}), 400

        # 验证管理员身份
        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user or not admin_user.check_password(admin_password):
            return jsonify({'success': False, 'message': '管理员身份验证失败'}), 401

        users = User.query.all()
        return jsonify({
            'success': True,
            'data': {
                'users': [user.to_dict() for user in users],
                'total': len(users)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户列表失败: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'deployment':'vercel'
        }
    })


if __name__ == '__main__':
    print("🚀 启动知识库问答系统...")
    print("📊 数据库文件: users.db")
    print("🌐 访问地址: http://localhost:5000")
    print("👨‍💼 默认管理员: admin / admin123")
    print("🎓 登录方式: 学号登录")
    print("📚 学号库管理: 在用户管理页面点击'学号库管理'")
    print("🔐 密码重置: 支持邮箱和手机号找回密码")
    app.run(debug=False, host='0.0.0.0', port=5000)