/**
 * ExDocIndex 通用 JavaScript 工具库
 */

// ========== Toast 提示系统 ==========

/**
 * 显示 Toast 提示
 * @param {string} message - 提示信息
 * @param {string} type - 提示类型：success, error, warning, info
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;
    
    container.appendChild(toast);
    
    // 3 秒后自动移除
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

// ========== 确认对话框系统 ==========

let confirmCallback = null;

/**
 * 显示确认对话框
 * @param {string} title - 标题
 * @param {string} message - 消息内容
 * @param {string} confirmText - 确认按钮文字
 * @param {string} cancelText - 取消按钮文字
 * @returns {Promise<boolean>} - 用户是否确认
 */
function showConfirm(title, message, confirmText = '确定', cancelText = '取消') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const cancelBtn = document.getElementById('confirm-cancel');
        const okBtn = document.getElementById('confirm-ok');
        
        titleEl.textContent = title;
        messageEl.textContent = message;
        okBtn.textContent = confirmText;
        cancelBtn.textContent = cancelText;
        
        // 显示对话框
        modal.style.display = 'block';
        
        // 设置回调
        confirmCallback = (result) => {
            modal.style.display = 'none';
            resolve(result);
        };
        
        // 绑定事件
        okBtn.onclick = () => {
            if (confirmCallback) confirmCallback(true);
            confirmCallback = null;
        };
        
        cancelBtn.onclick = () => {
            if (confirmCallback) confirmCallback(false);
            confirmCallback = null;
        };
        
        // 点击外部关闭
        modal.onclick = (e) => {
            if (e.target === modal) {
                if (confirmCallback) confirmCallback(false);
                confirmCallback = null;
            }
        };
    });
}

// ========== 工具函数 ==========

/**
 * HTML 转义
 * @param {string} text - 原始文本
 * @returns {string} - 转义后的文本
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} - 格式化后的大小
 */
function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let sizeNum = bytes;
    
    while (sizeNum >= 1024 && unitIndex < units.length - 1) {
        sizeNum /= 1024;
        unitIndex++;
    }
    
    return `${sizeNum.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * 格式化日期时间
 * @param {string} dateString - 日期字符串
 * @returns {string} - 格式化后的日期时间
 */
function formatDateTime(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * 防抖函数
 * @param {Function} func - 要执行的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} - 防抖后的函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要执行的函数
 * @param {number} limit - 时间限制（毫秒）
 * @returns {Function} - 节流后的函数
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ========== API 请求封装 ==========

/**
 * GET 请求
 * @param {string} url - 请求 URL
 * @returns {Promise<any>} - 响应数据
 */
async function httpGet(url) {
    const response = await fetch(url);
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || '请求失败');
    }
    
    return data;
}

/**
 * POST 请求
 * @param {string} url - 请求 URL
 * @param {Object} body - 请求体
 * @returns {Promise<any>} - 响应数据
 */
async function httpPost(url, body = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || '请求失败');
    }
    
    return data;
}

/**
 * DELETE 请求
 * @param {string} url - 请求 URL
 * @returns {Promise<any>} - 响应数据
 */
async function httpDelete(url) {
    const response = await fetch(url, {
        method: 'DELETE'
    });
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || '请求失败');
    }
    
    return data;
}

// ========== 全局事件绑定 ==========

document.addEventListener('DOMContentLoaded', () => {
    // 全局键盘事件
    document.addEventListener('keydown', (e) => {
        // ESC 关闭所有模态框
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                modal.style.display = 'none';
            });
        }
    });
    
    // 自动更新队列状态
    updateQueueStatus();
    setInterval(updateQueueStatus, 5000);
});

/**
 * 更新队列状态显示
 */
async function updateQueueStatus() {
    try {
        const response = await fetch('/api/tasks/queue');
        const data = await response.json();
        
        if (data.success) {
            const queueCount = document.getElementById('queue-count');
            if (queueCount) {
                queueCount.textContent = data.status.queue_size;
                
                // 如果有任务在运行，添加动画效果
                if (data.status.running) {
                    queueCount.parentElement.classList.add('status-running');
                } else {
                    queueCount.parentElement.classList.remove('status-running');
                }
            }
        }
    } catch (error) {
        console.error('更新队列状态失败:', error);
    }
}

// ========== 导出全局函数 ==========
window.showToast = showToast;
window.showConfirm = showConfirm;
window.escapeHtml = escapeHtml;
window.formatFileSize = formatFileSize;
window.formatDateTime = formatDateTime;
window.httpGet = httpGet;
window.httpPost = httpPost;
window.httpDelete = httpDelete;
