#!/usr/bin/env python3
import os
import sys
import json
import math
import base64
import shutil
import stat
import mimetypes
import hashlib
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory, make_response, redirect, abort
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration (override via environment variables)
PORT = int(os.environ.get('WEB_FILE_BROWSER_PORT', '3801'))
PASSWORD = os.environ.get('WEB_FILE_BROWSER_PASSWORD', 'mypassword')
# Root directory that the browser is allowed to expose.
# Defaults to the current user's home directory.
DEFAULT_ROOT = os.path.realpath(
    os.environ.get('WEB_FILE_BROWSER_ROOT', os.path.expanduser('~'))
)
ALLOWED_UPLOAD_EXTENSIONS = set(['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.html', '.css', '.js', '.json', '.xml', '.zip', '.tar', '.gz', '.rar', '.7z'])

def check_password(req):
    """Check password from query parameter, form data, or header"""
    password = req.args.get('password', '') or req.form.get('password', '') or req.headers.get('X-Password', '')
    return password == PASSWORD

def safe_path(raw_path):
    """Resolve *raw_path* and confine it to DEFAULT_ROOT.

    Returns the real (symlink-resolved) absolute path, or None if the path
    escapes the configured root. Using ``os.path.commonpath`` avoids the
    ``/root`` vs ``/root_evil`` prefix-matching pitfall of ``startswith``.
    """
    if not raw_path:
        return None
    # Resolve relative paths against the configured root, not the process cwd,
    # so results do not depend on where the server happens to be started.
    if not os.path.isabs(raw_path):
        raw_path = os.path.join(DEFAULT_ROOT, raw_path)
    candidate = os.path.realpath(os.path.normpath(raw_path))
    try:
        if os.path.commonpath([DEFAULT_ROOT, candidate]) != DEFAULT_ROOT:
            return None
    except ValueError:
        # Raised on Windows when paths are on different drives.
        return None
    return candidate

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/files', methods=['GET'])
def list_files():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    path = safe_path(request.args.get('path') or DEFAULT_ROOT)
    if path is None:
        return jsonify({'error': '路径越界'}), 400
    
    try:
        if not os.path.exists(path):
            return jsonify({'error': f'路径不存在: {path}'}), 404
        
        if not os.path.isdir(path):
            # Return file info for single file
            size = os.path.getsize(path)
            name = os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()
            return jsonify({
                'type': 'file',
                'name': name,
                'size': size,
                'path': path,
                'modified': datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S'),
                'is_dir': False
            })
        
        files = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                st = os.stat(item_path)
                is_dir = os.path.isdir(item_path)
                ext = ''
                if not is_dir:
                    ext = os.path.splitext(item)[1].lower()
                
                files.append({
                    'name': item,
                    'size': st.st_size if not is_dir else None,
                    'path': item_path,
                    'modified': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_dir': is_dir,
                    'extension': ext,
                    'created': datetime.fromtimestamp(st.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
            except (PermissionError, OSError) as e:
                files.append({
                    'name': item,
                    'size': None,
                    'path': item_path,
                    'modified': None,
                    'is_dir': os.path.isdir(item_path),
                    'extension': '',
                    'created': None,
                    'error': str(e)
                })
        
        # Sort: directories first, then by name
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        # Get parent path for navigation
        parent_path = os.path.dirname(path) if path != DEFAULT_ROOT and os.path.dirname(path) else ''
        
        return jsonify({
            'current_path': path,
            'parent_path': parent_path,
            'files': files,
            'root_path': DEFAULT_ROOT
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST', 'PUT'])
def upload_file():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    path = safe_path(request.form.get('path') or DEFAULT_ROOT)
    if path is None:
        return jsonify({'error': '路径越界'}), 400
    
    # Handle multipart form upload
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        filename = file.filename
        save_path = os.path.join(path, filename)
        
        # Handle duplicate filenames
        if os.path.exists(save_path):
            base, ext = os.path.splitext(filename)
            save_path = os.path.join(path, f"{base}_({int(datetime.now().timestamp())}){ext}")
        
        file.save(save_path)
        return jsonify({'success': True, 'path': save_path, 'name': filename})
    
    # Handle base64 encoded file upload
    try:
        data = json.loads(request.get_data())
        file_data = base64.b64decode(data.get('content', ''))
        filename = data.get('name', 'downloaded_file')
        save_path = os.path.join(path, filename)
        
        if os.path.exists(save_path):
            base, ext = os.path.splitext(filename)
            save_path = os.path.join(path, f"{base}_({int(datetime.now().timestamp())}){ext}")
        
        with open(save_path, 'wb') as f:
            f.write(file_data)
        
        return jsonify({'success': True, 'path': save_path, 'name': filename})
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/download', methods=['GET'])
def download_file():
    path = request.args.get('path')
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    full_path = safe_path(path)
    if full_path is None:
        return jsonify({'error': '路径越界'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.isdir(full_path):
        return send_from_directory(full_path, 'index.html')
    
    # Set MIME type
    mime_type = mimetypes.guess_type(full_path) or 'application/octet-stream'
    
    with open(full_path, 'rb') as f:
        data = f.read()
    
    response = make_response(data)
    response.headers['Content-Type'] = mime_type
    response.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(full_path)}"'
    return response

@app.route('/api/download_base64', methods=['GET'])
def download_base64():
    path = request.args.get('path')
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    full_path = safe_path(path)
    if full_path is None:
        return jsonify({'error': '路径越界'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        with open(full_path, 'rb') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': base64.b64encode(content).decode('utf-8'),
            'name': os.path.basename(full_path),
            'size': len(content)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_base64', methods=['POST'])
def upload_base64():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        file_data = base64.b64decode(data.get('content', ''))
        path = data.get('path', DEFAULT_ROOT)
        filename = data.get('name', 'downloaded_file')
        
        path = safe_path(path)
        if path is None:
            return jsonify({'error': '路径越界'}), 400
        
        save_path = os.path.join(path, filename)
        
        # Handle duplicate
        if os.path.exists(save_path):
            base, ext = os.path.splitext(filename)
            save_path = os.path.join(path, f"{base}_({int(datetime.now().timestamp())}){ext}")
        
        with open(save_path, 'wb') as f:
            f.write(file_data)
        
        return jsonify({'success': True, 'path': save_path, 'name': filename})
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/mkdir', methods=['POST'])
def create_directory():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        path = data.get('path', request.args.get('path', DEFAULT_ROOT))
        name = data.get('name', 'new_folder')
        
        path = safe_path(path)
        if path is None:
            return jsonify({'error': '路径越界'}), 400
        
        new_path = os.path.join(path, name)
        os.makedirs(new_path, exist_ok=True)
        
        return jsonify({'success': True, 'path': new_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rename', methods=['POST'])
def rename():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        old_path = data.get('path')
        new_name = (data.get('name') or '').strip()
        
        if not old_path:
            return jsonify({'error': '无效的路径'}), 400
        
        if not new_name:
            return jsonify({'error': '名称不能为空'}), 400
        
        if '/' in new_name or '\\' in new_name:
            return jsonify({'error': '名称不能包含斜杠'}), 400
        
        old_path = safe_path(old_path)
        
        if old_path is None:
            return jsonify({'error': '路径越界'}), 400
        
        if not os.path.exists(old_path):
            return jsonify({'error': '文件不存在'}), 404
        
        new_path = safe_path(os.path.join(os.path.dirname(old_path), new_name))
        
        if new_path is None:
            return jsonify({'error': '路径越界'}), 400
        
        if new_path != old_path and os.path.exists(new_path):
            return jsonify({'error': '目标名称已存在'}), 409
        
        os.rename(old_path, new_path)
        
        return jsonify({'success': True, 'path': new_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def delete():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        target = safe_path(data.get('path'))
        
        if target is None:
            return jsonify({'error': '路径越界'}), 400
        
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/copy', methods=['POST'])
def copy_file():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        source = safe_path(data.get('source'))
        destination_dir = safe_path(data.get('destination'))
        
        if source is None or destination_dir is None:
            return jsonify({'error': '路径越界'}), 400
        
        # Handle name conflict
        name = os.path.basename(source)
        dest_path = os.path.join(destination_dir, name)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(name)
            dest_path = os.path.join(destination_dir, f"{base}_({int(datetime.now().timestamp())}){ext}")
        
        if os.path.isdir(source):
            shutil.copytree(source, dest_path)
        else:
            shutil.copy2(source, dest_path)
        
        return jsonify({'success': True, 'path': dest_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/move', methods=['POST'])
def move_file():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        source = safe_path(data.get('source'))
        destination = safe_path(data.get('destination'))
        
        if source is None or destination is None:
            return jsonify({'error': '路径越界'}), 400
        
        # Handle name conflict
        name = os.path.basename(source)
        dest_path = os.path.join(destination, name)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(name)
            dest_path = os.path.join(destination, f"{base}_({int(datetime.now().timestamp())}){ext}")
        
        os.rename(source, dest_path)
        
        return jsonify({'success': True, 'path': dest_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_files():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        path = request.args.get('path', DEFAULT_ROOT)
        keyword = request.args.get('keyword', '')
        max_depth = int(request.args.get('depth', 3))
        path = safe_path(path)
        if path is None:
            return jsonify({'error': '路径越界'}), 400
        
        results = []
        for root, dirs, files in os.walk(path):
            depth = root.replace(path, '').count(os.sep)
            if depth > max_depth:
                continue
            
            for name in files:
                if keyword.lower() in name.lower():
                    full_path = os.path.join(root, name)
                    results.append({
                        'name': name,
                        'path': full_path,
                        'size': os.path.getsize(full_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'),
                        'is_dir': False
                    })
            
            for name in dirs:
                if keyword.lower() in name.lower():
                    full_path = os.path.join(root, name)
                    results.append({
                        'name': name,
                        'path': full_path,
                        'size': None,
                        'modified': None,
                        'is_dir': True
                    })
        
        results.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({'results': results, 'search_path': path, 'keyword': keyword})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clipboard', methods=['POST'])
def clipboard():
    """Simulate copy/paste via API"""
    try:
        data = json.loads(request.get_data())
        action = data.get('action', 'copy')
        items = data.get('items', [])
        
        # Store clipboard in memory
        app.clipboard = {'action': action, 'items': items}
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/info', methods=['GET'])
def info():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    path = request.args.get('path', DEFAULT_ROOT)
    path = safe_path(path)
    
    if path is None:
        return jsonify({'error': '路径越界'}), 400
    
    try:
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        
        return jsonify({
            'path': path,
            'name': os.path.basename(path),
            'is_dir': is_dir,
            'size': stat.st_size if not is_dir else None,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'access_mode': oct(stat.st_mode),
            'root_path': DEFAULT_ROOT
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/permissions', methods=['POST'])
def change_permissions():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        data = json.loads(request.get_data())
        path = safe_path(data.get('path'))
        mode = int(data.get('mode', 0o755))
        
        if path is None:
            return jsonify({'error': '路径越界'}), 400
        
        os.chmod(path, mode)
        return jsonify({'success': True, 'path': path, 'mode': oct(mode)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usage', methods=['GET'])
def disk_usage():
    if not check_password(request):
        return jsonify({'error': '密码错误'}), 401
    
    try:
        total, used, free = shutil.disk_usage(DEFAULT_ROOT)
        return jsonify({
            'total': total,
            'used': used,
            'free': free,
            'total_human': format_size(total),
            'used_human': format_size(used),
            'free_human': format_size(free)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = max(0, min(len(units) - 1, int(math.log(max(size_bytes, 1), 1024))))
    return f'{size_bytes / (1024 ** index):.2f} {units[index]}'

if __name__ == '__main__':
    # Never enable the Werkzeug debugger by default: it allows remote code
    # execution. Opt in explicitly with WEB_FILE_BROWSER_DEBUG=1.
    DEBUG = os.environ.get('WEB_FILE_BROWSER_DEBUG', '0') == '1'

    print(f"启动 Web 文件浏览器 / Web File Browser")
    print(f"端口 / Port: {PORT}")
    print(f"根目录 / Root: {DEFAULT_ROOT}")
    if PASSWORD == 'mypassword':
        print("⚠️  正在使用默认密码，请通过 WEB_FILE_BROWSER_PASSWORD 环境变量修改")
        print("⚠️  Using default password; set WEB_FILE_BROWSER_PASSWORD to change it")
    print(f"访问地址 / URL: http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
