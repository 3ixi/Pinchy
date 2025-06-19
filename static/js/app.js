// Pinchy 前端应用主逻辑

function app() {
    return {
        // 认证状态
        isAuthenticated: false,
        user: null,
        loading: false,
        
        // 当前页面
        currentPage: 'dashboard',

        // 移动端菜单
        mobileMenuOpen: false,

        // WebSocket连接
        ws: null,
        wsConnected: false,

        // 任务日志WebSocket连接
        taskLogWs: null,
        // 标记是否已经接收到第一行输出
        hasReceivedFirstOutput: false,
        // 防重复toast的消息ID记录
        processedMessages: new Set(),
        // 停止任务相关
        showStopTaskConfirmModal: false,
        stopTaskTarget: null,
        stopTaskLoading: false,

        // Toast消息
        toasts: [],
        toastId: 0,

        // 模态框状态
        showTaskModal: false,
        showUploadModal: false,
        showCreateTextModal: false,
        showCreateDirModal: false,
        showEnvModal: false,
        showPackageModal: false,
        showPackageInstallModal: false,
        showChangeUsernameModal: false,
        showAgreementModal: false,
        showTermsModal: false,
        showDataCollectionModal: false,

        // 接口调试相关
        debugConfigs: [],
        showDebugConfigModal: false,
        editingDebugConfig: null,

        // 脚本订阅相关
        subscriptions: [],
        subscriptionsLoading: false,
        showSubscriptionModal: false,
        editingSubscription: null,
        syncingSubscriptions: new Set(), // 正在同步的订阅ID集合
        subscriptionForm: {
            name: '',
            description: '',
            git_url: '',
            save_directory: '',
            file_extensions: '',
            exclude_patterns: '',
            include_folders: true,
            include_subfolders: true,
            use_proxy: false,
            sync_delete_removed_files: false,
            cron_expression: '0 0 * * *',
            notification_enabled: false,
            notification_type: ''
        },
        subscriptionLogs: [],
        subscriptionLogsLoading: false,
        showSubscriptionLogsModal: false,
        currentSubscriptionLogs: null,
        proxyConfig: {
            enabled: false,
            host: '',
            port: 0
        },
        showProxyConfigModal: false,
        // requirements.txt依赖检查相关
        showRequirementsModal: false,
        requirementsData: null,
        requirementsLoading: false,
        currentRequirementsSubscription: null,
        debugConfigForm: {
            name: '',
            description: '',
            method: 'GET',
            url: '',
            headers: {},
            headersText: '',
            payload: '',
            notification_type: '',
            notification_enabled: false,
            notification_condition: 'always',
            cron_expression: '',
            is_active: false
        },
        quickDebugForm: {
            method: 'GET',
            url: '',
            headers: [
                { key: 'Host', value: '', readonly: true },
                { key: 'Content-Length', value: '自动计算', readonly: true },
                { key: 'User-Agent', value: 'Pinchy/1.0.0', readonly: false }
            ],
            payload: '',
            notification_type: '',
            notification_enabled: false,
            notification_condition: 'always'
        },
        quickDebugResult: null,
        quickDebugExecuting: false,
        responseTab: 'body',
        showImportModal: false,
        importContent: '',
        showVariablesModal: false,
        availableVariables: [],
        showChangePasswordModal: false,
        showPreviewModal: false,
        showRenameModal: false,
        showNotificationConfigModal: false,
        showTaskLogModal: false,
        showCronGeneratorModal: false,
        showExtractModal: false,

        // 编辑状态
        editingTask: null,
        editingEnv: null,
        editingNotificationConfig: null,
        currentTaskLog: null,
        taskLogData: null,
        taskLogLoading: false,
        taskLogTab: 'output',
        logPollingTimer: null, // 日志轮询定时器

        // Cron生成器相关
        cronForm: {
            minute: '*',
            hour: '*',
            day: '*',
            month: '*',
            weekday: '*'
        },
        generatedCron: '* * * * *',

        // 表单数据
        taskForm: {
            name: '',
            description: '',
            script_path: '',
            script_type: 'python',
            cron_expression: '',
            environment_vars: {}
        },
        envForm: {
            key: '',
            value: '',
            description: ''
        },
        packageForm: {
            package_type: 'python',
            package_name: '',
            version: ''
        },
        usernameForm: {
            new_username: '',
            password: ''
        },
        passwordForm: {
            old_password: '',
            new_password: '',
            confirm_password: ''
        },
        textFileForm: {
            filename: '',
            content: ''
        },

        // 数据
        tasks: [],
        taskExecutions: {}, // 任务执行记录，key为task_id
        runningTasks: new Set(), // 正在运行的任务ID集合
        manualRunTasks: new Set(), // 手动运行的任务ID集合
        files: [],
        logs: [],
        envVars: [],
        pythonPackages: [],
        nodejsPackages: [],
        filteredPythonPackages: [],
        filteredNodejsPackages: [],
        packageSearchQuery: '',

        // 包安装日志相关
        packageInstallStatus: 'idle', // idle, installing, success, failed
        packageInstallLogs: [],
        packageInstallInfo: {
            type: '',
            name: '',
            version: ''
        },
        packageLogId: 0,
        packageOperationType: 'install', // install, uninstall

        // 状态
        currentPath: '',
        selectedFile: null,
        newDirName: '',
        currentPreviewFile: null,
        previewFileData: null, // 用于模态框显示的文件数据
        previewContent: '',
        previewLoading: false,
        isEditingFile: false,
        editContent: '',
        saveLoading: false,
        renameForm: {
            file: null,
            newName: ''
        },
        extractForm: {
            file: null
        },
        logFilter: {
            taskId: '',
            status: ''
        },
        logPagination: {
            currentPage: 1,
            pageSize: 20,
            total: 0,
            totalPages: 0
        },
        logCleanupSettings: {
            enabled: false,
            retentionDays: 7
        },
        packageTab: 'python',
        packageManagerConfig: null,

        // 通知服务相关
        notificationConfigs: [],
        notificationConfigsLoading: true,
        activeNotificationConfigs: [],
        taskNotificationConfigs: {},
        testingNotifications: new Set(), // 正在测试的通知配置ID集合
        notificationConfigForm: {
            name: '',
            config: {}
        },

        // SendNotify配置相关
        sendNotifyConfig: {
            notification_type: ''
        },
        sendNotifyConfigLoading: false,
        sendNotifyConfigSaving: false,

        // 配色方案相关
        currentColorScheme: 'blue',
        colorSchemes: [
            { id: 'blue', name: '蓝色主题', primary: 'blue', description: '经典蓝色配色方案', colors: ['#3b82f6', '#2563eb', '#1d4ed8'] },
            { id: 'green', name: '绿色主题', primary: 'green', description: '清新绿色配色方案', colors: ['#22c55e', '#16a34a', '#15803d'] },
            { id: 'purple', name: '紫色主题', primary: 'purple', description: '优雅紫色配色方案', colors: ['#a855f7', '#9333ea', '#7c3aed'] },
            { id: 'gray', name: '灰色主题', primary: 'gray', description: '简约灰色配色方案', colors: ['#6b7280', '#4b5563', '#374151'] },
            { id: 'orange', name: '橙色主题', primary: 'orange', description: '活力橙色配色方案', colors: ['#f97316', '#ea580c', '#c2410c'] },
            { id: 'dark', name: '深色主题', primary: 'dark', description: '适合暗光环境的深色配色方案', colors: ['#6b7280', '#4b5563', '#374151'], icon: 'fas fa-moon' }
        ],

        // 加载状态
        tasksLoading: false,
        filesLoading: false,
        logsLoading: false,
        envVarsLoading: false,
        packagesLoading: false,
        systemInfoLoading: false,
        dashboardLoading: false,

        systemInfo: null,
        systemVersion: '',
        environmentCheck: null,

        // 时区配置相关
        timezoneConfig: null,
        timezoneConfigLoading: false,
        selectedTimezone: '',
        timezoneUpdating: false,
        
        // 登录表单
        loginForm: {
            username: '',
            password: '',
            captcha_answer: '',
            mfa_code: ''
        },

        // 安全相关
        securityStatus: {
            captcha_enabled: false,
            ip_blocking_enabled: false,
            mfa_enabled: false,
            show_captcha: false,  // 是否显示验证码
            is_ip_locked: false,
            failed_attempts: 0
        },
        captchaImage: '',
        mfaCodeSending: false,
        mfaCodeCooldown: 0,
        mfaCodeTimer: null,

        // 安全配置
        securityConfig: {
            captcha_enabled: false,
            ip_blocking_enabled: false,
            mfa_enabled: false,
            mfa_notification_type: '',
            available_notifications: []
        },
        securityConfigLoading: false,
        securityConfigSaving: false,
        
        // 统计数据
        stats: {
            totalTasks: 0,
            activeTasks: 0,
            todayExecutions: 0,
            failedTasks: 0
        },
        
        // 最近日志
        recentLogs: [],

        // 版本升级相关
        versionInfo: {
            current_version: '',
            latest_version: '',
            has_update: false,
            upgrade_date: '',
            download_url: '',
            upgrade_info: ''
        },
        showVersionModal: false,

        // 命令配置相关
        commandConfig: {
            python_command: 'python',
            nodejs_command: 'node',
            python_package_manager: 'pip',
            nodejs_package_manager: 'npm'
        },
        originalCommandConfig: null,
        commandTestResult: {
            python: null,
            nodejs: null
        },
        packageManagerTestResult: {
            python: null,
            nodejs: null
        },
        isTestingCommand: false,
        isTestingPackageManager: false,
        isSavingCommandConfig: false,
        
        // 数据加载状态跟踪
        dataLoaded: {
            dashboard: false,
            tasks: false,
            files: false,
            notifications: false,
            subscriptions: false,
            debugConfigs: false,
            envVars: false,
            packages: false,
            logs: false,
            systemInfo: false
        },

        // 初始化
        async init() {
            await this.checkAuth();
            await this.loadSystemVersion();
            await this.checkEnvironment();
            await this.loadColorScheme(); // 总是加载配色方案
            await this.loadSecurityStatus(); // 加载安全状态

            // 监听窗口大小变化，用于响应式截断
            window.addEventListener('resize', () => {
                // 重新渲染环境变量列表以应用新的截断长度
                if (this.currentPage === 'env') {
                    // 触发重新渲染 - 使用 Alpine.js 的方式
                    const envVarsCopy = [...this.envVars];
                    this.envVars = [];
                    setTimeout(() => {
                        this.envVars = envVarsCopy;
                    }, 0);
                }
            });

            if (this.isAuthenticated) {
                this.connectWebSocket();
                // 只加载仪表板必需的数据
                await this.loadDashboardData();
                // 初始获取运行状态
                await this.loadRunningTasksStatus();
                // 自动检查版本更新
                await this.checkVersionUpdate();
            } else {
                // 如果需要验证码，自动加载验证码
                if (this.securityStatus.show_captcha) {
                    await this.refreshCaptcha();
                }
            }
        },

        // 加载系统版本
        async loadSystemVersion() {
            try {
                const response = await fetch('/api/settings/version');
                if (response.ok) {
                    const data = await response.json();
                    this.systemVersion = `v${data.version}`;
                }
            } catch (error) {
                console.error('加载系统版本失败:', error);
                this.systemVersion = 'v1.0.1'; // 默认版本
            }
        },

        // 检查环境
        async checkEnvironment() {
            try {
                const response = await fetch('/api/settings/check-environment');
                if (response.ok) {
                    this.environmentCheck = await response.json();
                }
            } catch (error) {
                console.error('检查环境失败:', error);
            }
        },

        // 加载包管理器配置
        async loadPackageManagerConfig() {
            try {
                const response = await fetch('/api/packages/manager-config');
                if (response.ok) {
                    this.packageManagerConfig = await response.json();
                }
            } catch (error) {
                console.error('加载包管理器配置失败:', error);
                this.packageManagerConfig = {
                    python_package_manager: 'pip',
                    nodejs_package_manager: 'npm'
                };
            }
        },

        // 检查认证状态
        async checkAuth() {
            try {
                const response = await fetch('/api/auth/me');
                if (response.ok) {
                    this.user = await response.json();
                    this.isAuthenticated = true;
                }
            } catch (error) {
                console.error('检查认证状态失败:', error);
            }
        },
        
        // 登录
        async login() {
            this.loading = true;
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(this.loginForm)
                });

                const data = await response.json();

                if (response.ok) {
                    this.user = data.user;
                    this.isAuthenticated = true;
                    this.showToast('登录成功', 'success');
                    await this.loadColorScheme(); // 登录后立即加载配色方案

                    // 延迟连接WebSocket，确保认证状态已设置
                    setTimeout(() => {
                        this.connectWebSocket();
                    }, 100);

                    await this.loadDashboardData();
                    // 初始获取运行状态
                    await this.loadRunningTasksStatus();
                } else {
                    this.showToast(data.detail || '登录失败', 'error');
                    // 登录失败后重新加载安全状态，检查是否需要显示验证码
                    await this.loadSecurityStatus();
                    // 如果需要验证码，自动加载验证码
                    if (this.securityStatus.show_captcha) {
                        await this.refreshCaptcha();
                    }
                }
            } catch (error) {
                this.showToast('网络错误，请稍后重试', 'error');
                console.error('登录失败:', error);
            } finally {
                this.loading = false;
            }
        },
        
        // 登出
        async logout() {
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
                this.isAuthenticated = false;
                this.user = null;
                this.currentPage = 'dashboard';
                this.disconnectWebSocket();
                this.showToast('已登出', 'info');
                // 重新加载安全状态
                await this.loadSecurityStatus();
            } catch (error) {
                console.error('登出失败:', error);
            }
        },

        // 加载安全状态
        async loadSecurityStatus() {
            try {
                const response = await fetch('/api/auth/security-status');
                if (response.ok) {
                    this.securityStatus = await response.json();
                }
            } catch (error) {
                console.error('加载安全状态失败:', error);
            }
        },

        // 刷新验证码
        async refreshCaptcha() {
            try {
                const response = await fetch('/api/auth/captcha');
                if (response.ok) {
                    const data = await response.json();
                    this.captchaImage = data.image_data;
                }
            } catch (error) {
                console.error('获取验证码失败:', error);
                this.showToast('获取验证码失败', 'error');
            }
        },

        // 发送MFA验证码
        async sendMFACode() {
            if (this.mfaCodeSending || this.mfaCodeCooldown > 0) {
                return;
            }

            this.mfaCodeSending = true;
            try {
                const response = await fetch('/api/auth/send-mfa-code', {
                    method: 'POST'
                });

                if (response.ok) {
                    this.showToast('验证码已发送', 'success');
                    this.startMFACodeCooldown();
                } else {
                    const data = await response.json();
                    this.showToast(data.detail || '发送验证码失败', 'error');
                }
            } catch (error) {
                console.error('发送验证码失败:', error);
                this.showToast('发送验证码失败', 'error');
            } finally {
                this.mfaCodeSending = false;
            }
        },

        // 开始MFA验证码冷却
        startMFACodeCooldown() {
            this.mfaCodeCooldown = 60;
            this.mfaCodeTimer = setInterval(() => {
                this.mfaCodeCooldown--;
                if (this.mfaCodeCooldown <= 0) {
                    clearInterval(this.mfaCodeTimer);
                    this.mfaCodeTimer = null;
                }
            }, 1000);
        },
        
        // 连接WebSocket
        connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            console.log('尝试连接WebSocket:', wsUrl);
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.wsConnected = true;
                console.log('WebSocket连接已建立');
                // 延迟发送ping消息，确保连接完全建立
                setTimeout(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('ping');
                    }
                }, 100);
            };

            this.ws.onmessage = (event) => {
                // console.log('收到WebSocket消息:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error, event.data);
                }
            };

            this.ws.onclose = (event) => {
                this.wsConnected = false;
                console.log('WebSocket连接已断开, 代码:', event.code, '原因:', event.reason);

                // 显示连接断开提示
                if (event.code !== 1000) { // 1000是正常关闭代码
                    this.showToast('WS服务已断开连接', 'error');
                }

                // 尝试重连
                setTimeout(() => {
                    if (this.isAuthenticated) {
                        console.log('尝试重新连接WebSocket...');
                        this.connectWebSocket();
                    }
                }, 5000);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.wsConnected = false;
                this.showToast('服务端连接异常', 'error');
            };
        },
        
        // 断开WebSocket
        disconnectWebSocket() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
                this.wsConnected = false;
            }
        },
        
        // 处理WebSocket消息
        handleWebSocketMessage(data) {
            // 生成消息唯一ID，防止重复处理
            let messageId;
            if (data.type.startsWith('package_')) {
                // 包管理消息使用包名、类型和时间戳生成ID
                const timestamp = Date.now();
                const packageInfo = `${data.package_type || 'unknown'}_${data.package_name || 'unknown'}`;
                if (data.output) {
                    // 对于输出消息，使用输出内容的哈希值
                    const outputHash = this.simpleHash(data.output);
                    messageId = `${data.type}_${packageInfo}_${outputHash}`;
                } else {
                    // 对于开始/完成消息，使用时间戳
                    messageId = `${data.type}_${packageInfo}_${timestamp}`;
                }
            } else if (data.type.startsWith('subscription_sync_')) {
                // 订阅同步消息使用订阅ID和类型生成ID
                messageId = `${data.type}_${data.subscription_id}_${data.log_id || Date.now()}`;
            } else {
                // 任务消息使用原有逻辑
                messageId = `${data.type}_${data.task_id}_${data.log_id || Date.now()}`;
            }

            // 如果已经处理过这个消息，跳过
            if (this.processedMessages.has(messageId)) {
                // console.log('跳过重复消息:', messageId);
                return;
            }
            this.processedMessages.add(messageId);
            // console.log('处理消息:', messageId);

            // 清理旧的消息ID（保留最近100个）
            if (this.processedMessages.size > 100) {
                const messages = Array.from(this.processedMessages);
                this.processedMessages.clear();
                messages.slice(-50).forEach(id => this.processedMessages.add(id));
            }

            switch (data.type) {
                case 'task_start':
                    if (data.task_id) {
                        this.runningTasks.add(data.task_id);

                        // 显示任务开始消息
                        if (this.manualRunTasks.has(data.task_id)) {
                            // 手动运行的任务显示绿色消息
                            this.showToast(`任务 ${data.task_name} 开始执行`, 'success');
                        } else {
                            // 自动运行的任务显示蓝色消息
                            this.showToast(`任务 ${data.task_name} 自动开始执行`, 'info');
                        }

                        // 如果当前正在查看这个任务的日志，初始化实时日志显示
                        if (this.currentTaskLog && this.currentTaskLog.id === data.task_id) {
                            this.initRealTimeLogDisplay(data.log_id);
                        }
                    }
                    break;
                case 'task_output':
                    // 处理实时输出
                    this.handleRealTimeOutput(data);
                    break;
                case 'task_complete':
                    if (data.task_id) {
                        this.runningTasks.delete(data.task_id);

                        // 根据任务状态显示不同的toast消息
                        let message, toastType;
                        if (data.status === 'success') {
                            message = `任务 ${data.task_name} 执行成功`;
                            toastType = 'success';
                        } else if (data.status === 'stopped') {
                            message = `任务 ${data.task_name} 已停止`;
                            toastType = 'info';
                        } else {
                            message = `任务 ${data.task_name} 执行失败`;
                            toastType = 'error';
                        }

                        this.showToast(message, toastType);

                        // 清除手动运行标记
                        if (this.manualRunTasks.has(data.task_id)) {
                            this.manualRunTasks.delete(data.task_id);
                        }

                        // 如果当前正在查看这个任务的日志，刷新日志并停止轮询
                        if (this.currentTaskLog && this.currentTaskLog.id === data.task_id) {
                            this.refreshTaskLog();
                            // 任务完成后停止实时监控
                            setTimeout(() => {
                                this.stopRealTimeLogMonitoring();
                            }, 1000);
                        }
                    }
                    this.loadDashboardData(); // 刷新统计数据
                    break;
                case 'task_error':
                    if (data.task_id) {
                        this.runningTasks.delete(data.task_id);

                        // 显示toast提醒（全局提醒，在任何页面都能看到）
                        this.showToast(`任务 ${data.task_name} 执行出错: ${data.error}`, 'error');

                        // 清除手动运行标记
                        if (this.manualRunTasks.has(data.task_id)) {
                            this.manualRunTasks.delete(data.task_id);
                        }
                    }
                    break;
                case 'package_install_start':
                    // 包安装开始
                    this.packageInstallStatus = 'installing';
                    this.packageOperationType = 'install';
                    this.packageInstallInfo = {
                        type: data.package_type,
                        name: data.package_name,
                        version: data.version || ''
                    };
                    this.addPackageInstallLog(`开始安装 ${data.package_type} 包: ${data.package_name}${data.version ? ' (版本: ' + data.version + ')' : ''}`);
                    break;
                case 'package_install_output':
                    // 包安装输出
                    this.addPackageInstallLog(data.output);
                    break;
                case 'package_install_complete':
                    // 包安装完成
                    this.packageInstallStatus = data.success ? 'success' : 'failed';
                    this.addPackageInstallLog(data.success ? '✓ 安装成功' : '✗ 安装失败');
                    if (data.success) {
                        this.showToast(`包 ${this.packageInstallInfo.name} 安装成功`, 'success');
                        // 刷新包列表
                        setTimeout(() => {
                            this.loadPackages();
                        }, 1000);
                    } else {
                        this.showToast(`包 ${this.packageInstallInfo.name} 安装失败`, 'error');
                    }
                    break;
                case 'package_uninstall_start':
                    // 包卸载开始
                    this.packageInstallStatus = 'installing'; // 复用安装状态
                    this.packageOperationType = 'uninstall';
                    this.packageInstallInfo = {
                        type: data.package_type,
                        name: data.package_name,
                        version: ''
                    };
                    this.addPackageInstallLog(`开始卸载 ${data.package_type} 包: ${data.package_name}`);
                    // 显示日志模态框
                    this.showPackageInstallModal = true;
                    break;
                case 'package_uninstall_output':
                    // 包卸载输出
                    this.addPackageInstallLog(data.output);
                    break;
                case 'package_uninstall_complete':
                    // 包卸载完成
                    this.packageInstallStatus = data.success ? 'success' : 'failed';
                    this.addPackageInstallLog(data.success ? '✓ 卸载成功' : '✗ 卸载失败');
                    if (data.success) {
                        this.showToast(`包 ${data.package_name} 卸载成功`, 'success');
                        // 刷新包列表
                        setTimeout(() => {
                            this.loadPackages();
                        }, 1000);
                    } else {
                        this.showToast(`包 ${data.package_name} 卸载失败`, 'error');
                    }
                    break;
                case 'subscription_sync_start':
                    // 订阅同步开始
                    if (data.subscription_id) {
                        this.syncingSubscriptions.add(data.subscription_id);
                        console.log(`订阅 ${data.subscription_name} 开始同步`);
                    }
                    break;
                case 'subscription_sync_complete':
                    // 订阅同步完成
                    if (data.subscription_id) {
                        this.syncingSubscriptions.delete(data.subscription_id);

                        if (data.status === 'success') {
                            this.showToast(`订阅 "${data.subscription_name}" 同步完成`, 'success');
                        } else {
                            this.showToast(`订阅 "${data.subscription_name}" 同步失败`, 'error');
                        }

                        // 如果当前在订阅页面，重新加载订阅列表
                        if (this.currentPage === 'subscriptions') {
                            this.loadSubscriptions();
                        }
                    }
                    break;
            }
        },

        // 简单哈希函数
        simpleHash(str) {
            let hash = 0;
            if (str.length === 0) return hash;
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash; // 转换为32位整数
            }
            return Math.abs(hash);
        },



        // 加载仪表板数据
        async loadDashboardData() {
            this.dashboardLoading = true;
            try {
                // 加载统计数据
                await Promise.all([
                    this.loadStats(),
                    this.loadRecentLogs()
                ]);
            } catch (error) {
                console.error('加载仪表板数据失败:', error);
            } finally {
                this.dashboardLoading = false;
            }
        },
        
        // 加载统计数据
        async loadStats() {
            try {
                const [tasksResponse, logsResponse] = await Promise.all([
                    fetch('/api/tasks/'),
                    fetch('/api/logs/stats/summary')
                ]);
                
                if (tasksResponse.ok) {
                    const tasks = await tasksResponse.json();
                    this.stats.totalTasks = tasks.length;
                    this.stats.activeTasks = tasks.filter(t => t.is_active).length;
                }
                
                if (logsResponse.ok) {
                    const logStats = await logsResponse.json();
                    this.stats.todayExecutions = logStats.total;
                    this.stats.failedTasks = logStats.failed;
                }
            } catch (error) {
                console.error('加载统计数据失败:', error);
            }
        },
        
        // 加载最近日志
        async loadRecentLogs() {
            try {
                const response = await fetch('/api/logs/?limit=5');
                if (response.ok) {
                    const data = await response.json();
                    // 处理分页响应格式
                    if (data.items) {
                        this.recentLogs = data.items;
                    } else {
                        this.recentLogs = data;
                    }
                } else {
                    this.recentLogs = [];
                }
            } catch (error) {
                console.error('加载最近日志失败:', error);
                this.recentLogs = [];
            }
        },
        
        // 显示Toast消息
        showToast(message, type = 'info') {
            const toast = {
                id: ++this.toastId,
                message,
                type,
                show: true
            };

            this.toasts.push(toast);

            // 3秒后自动移除
            setTimeout(() => {
                this.removeToast(toast.id);
            }, 3000);
        },
        
        // 移除Toast消息
        removeToast(id) {
            const index = this.toasts.findIndex(t => t.id === id);
            if (index > -1) {
                this.toasts[index].show = false;
                setTimeout(() => {
                    this.toasts.splice(index, 1);
                }, 300);
            }
        },
        
        // 获取页面标题
        getPageTitle() {
            const titles = {
                dashboard: '仪表板',
                tasks: '任务管理',
                files: '文件管理',
                logs: '执行日志',
                subscriptions: '脚本订阅',
                env: '环境变量',
                packages: '包管理',
                notifications: '通知服务',
                'api-debug': '接口调试',
                settings: '系统设置'
            };
            return titles[this.currentPage] || '未知页面';
        },
        
        // 格式化日期时间
        formatDateTime(dateString) {
            // 如果后端已经返回了格式化的时间字符串（不包含T或Z），直接使用
            if (typeof dateString === 'string' &&
                dateString.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
                // 后端已经格式化为本地时区时间，直接转换显示格式
                const [datePart, timePart] = dateString.split(' ');
                const [year, month, day] = datePart.split('-');
                const [hours, minutes, seconds] = timePart.split(':');
                return `${parseInt(month)}月${parseInt(day)}日 ${hours}:${minutes}:${seconds}`;
            }

            // 对于ISO格式的时间字符串，按原来的方式处理
            const date = new Date(dateString);
            const month = date.getMonth() + 1;
            const day = date.getDate();
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            const seconds = date.getSeconds().toString().padStart(2, '0');
            return `${month}月${day}日 ${hours}:${minutes}:${seconds}`;
        },

        // 格式化日期（仅年月日）
        formatDateOnly(dateString) {
            const date = new Date(dateString);
            const month = date.getMonth() + 1;
            const day = date.getDate();
            return `${date.getFullYear()}年${month}月${day}日`;
        },
        
        // 获取状态文本
        getStatusText(status) {
            const statusMap = {
                success: '成功',
                failed: '失败',
                running: '运行中'
            };
            return statusMap[status] || status;
        },
        
        // API请求辅助函数
        async apiRequest(url, options = {}) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });

                if (!response.ok) {
                    const error = await response.json();
                    console.error('API错误详情:', error);
                    console.error('响应状态:', response.status, response.statusText);
                    throw new Error(error.detail || '请求失败');
                }

                return await response.json();
            } catch (error) {
                // 处理网络连接错误
                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    this.showToast('服务端已断开连接', 'error');
                } else if (error.message === 'Failed to fetch') {
                    this.showToast('服务端已断开连接', 'error');
                } else {
                    this.showToast(error.message, 'error');
                }
                throw error;
            }
        },

        // 任务管理方法
        async loadTasks() {
            this.tasksLoading = true;
            try {
                this.tasks = await this.apiRequest('/api/tasks/');
                // 加载每个任务的最近执行记录
                await this.loadTaskExecutions();
            } catch (error) {
                console.error('加载任务失败:', error);
                this.tasks = [];
            } finally {
                this.tasksLoading = false;
            }
        },

        async loadTaskExecutions() {
            try {
                // 为每个任务加载最近一次执行记录
                const promises = this.tasks.map(async (task) => {
                    try {
                        const response = await this.apiRequest(`/api/logs/?task_id=${task.id}&limit=1`);
                        // 处理分页响应格式
                        let logs;
                        if (response.items) {
                            logs = response.items;
                        } else {
                            logs = response;
                        }
                        if (logs && logs.length > 0) {
                            this.taskExecutions[task.id] = logs[0];
                        }
                    } catch (error) {
                        console.error(`加载任务 ${task.id} 执行记录失败:`, error);
                    }
                });
                await Promise.all(promises);
            } catch (error) {
                console.error('加载任务执行记录失败:', error);
            }
        },

        resetTaskForm() {
            this.taskForm = {
                name: '',
                description: '',
                script_path: '',
                script_type: 'python',
                cron_expression: '',
                environment_vars: {}
            };
        },

        editTask(task) {
            this.editingTask = task;
            this.taskForm = { ...task };
            this.showTaskModal = true;
        },

        async saveTask() {
            // 检查环境
            if (this.environmentCheck) {
                if (this.taskForm.script_type === 'python' && !this.environmentCheck.python.installed) {
                    this.showToast('请先安装Python环境才能添加Python任务', 'error');
                    return;
                }
                if (this.taskForm.script_type === 'nodejs' && !this.environmentCheck.nodejs.installed) {
                    this.showToast('请先安装Node.js环境才能添加Node.js任务', 'error');
                    return;
                }
            }

            try {
                if (this.editingTask) {
                    await this.apiRequest(`/api/tasks/${this.editingTask.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(this.taskForm)
                    });
                    this.showToast('任务更新成功', 'success');
                } else {
                    await this.apiRequest('/api/tasks/', {
                        method: 'POST',
                        body: JSON.stringify(this.taskForm)
                    });
                    this.showToast('任务创建成功', 'success');
                }
                this.showTaskModal = false;
                await this.loadTasks();
                this.dataLoaded.tasks = true;
            } catch (error) {
                console.error('保存任务失败:', error);
            }
        },

        async toggleTask(task) {
            try {
                await this.apiRequest(`/api/tasks/${task.id}/toggle`, {
                    method: 'POST'
                });
                this.showToast(`任务已${task.is_active ? '禁用' : '启用'}`, 'success');
                await this.loadTasks();
                this.dataLoaded.tasks = true;
            } catch (error) {
                console.error('切换任务状态失败:', error);
            }
        },

        async deleteTask(task) {
            if (!confirm(`确定要删除任务 "${task.name}" 吗？`)) return;

            try {
                await this.apiRequest(`/api/tasks/${task.id}`, {
                    method: 'DELETE'
                });
                this.showToast('任务删除成功', 'success');
                await this.loadTasks();
            } catch (error) {
                console.error('删除任务失败:', error);
            }
        },

        // 任务时间相关方法
        getTaskLastRunTime(taskId) {
            const execution = this.taskExecutions[taskId];
            if (!execution || !execution.start_time) {
                return '从未运行';
            }
            return this.formatDateTime(execution.start_time);
        },

        getTaskNextRunTime(task) {
            if (!task.is_active) {
                return '已禁用';
            }

            // 改进的cron表达式解析
            try {
                const cronParts = task.cron_expression.split(' ');
                if (cronParts.length !== 5) {
                    return '表达式格式错误';
                }

                const [minute, hour, day, month, weekday] = cronParts;

                // 生成描述性文本
                let description = this.generateCronDescription(minute, hour, day, month, weekday);

                // 如果能计算出具体的下次执行时间，优先显示
                const nextTime = this.calculateNextCronTime(task.cron_expression);
                if (nextTime) {
                    return nextTime;
                }

                return description || '根据计划执行';
            } catch (error) {
                console.error('解析cron表达式失败:', error);
                return '表达式解析错误';
            }
        },

        // 生成Cron表达式的描述
        generateCronDescription(minute, hour, day, month, weekday) {
            // 处理分钟间隔
            if (minute.startsWith('*/')) {
                const interval = parseInt(minute.substring(2));
                return `每${interval}分钟`;
            }

            // 处理小时间隔
            if (hour.startsWith('*/') && minute === '0') {
                const interval = parseInt(hour.substring(2));
                return `每${interval}小时`;
            }

            // 处理每小时执行
            if (minute !== '*' && hour === '*') {
                return `每小时第${minute}分钟`;
            }

            // 处理每天执行
            if (minute !== '*' && hour !== '*' && day === '*' && month === '*' && weekday === '*') {
                const h = parseInt(hour);
                const m = parseInt(minute);
                return `每天 ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
            }

            // 处理每周执行
            if (minute !== '*' && hour !== '*' && weekday !== '*' && day === '*') {
                const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                const h = parseInt(hour);
                const m = parseInt(minute);
                const wd = parseInt(weekday);
                return `每${weekdays[wd]} ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
            }

            // 处理每月执行
            if (minute !== '*' && hour !== '*' && day !== '*' && month === '*' && weekday === '*') {
                const h = parseInt(hour);
                const m = parseInt(minute);
                const d = parseInt(day);
                return `每月${d}日 ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
            }

            // 处理特定月份执行
            if (minute !== '*' && hour !== '*' && day !== '*' && month !== '*') {
                const months = ['', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
                const h = parseInt(hour);
                const m = parseInt(minute);
                const d = parseInt(day);
                const mon = parseInt(month);
                return `${months[mon]}${d}日 ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
            }

            return '';
        },

        // 计算下次cron执行时间
        calculateNextCronTime(cronExpression) {
            try {
                const cronParts = cronExpression.split(' ');
                if (cronParts.length !== 5) return null;

                const [minute, hour, day, month, weekday] = cronParts;
                const now = new Date();
                let next = new Date(now);
                next.setSeconds(0, 0); // 重置秒和毫秒

                // 处理分钟间隔 (如 */5)
                if (minute.startsWith('*/')) {
                    const interval = parseInt(minute.substring(2));
                    const currentMinute = now.getMinutes();
                    const nextMinute = Math.ceil((currentMinute + 1) / interval) * interval;

                    if (nextMinute >= 60) {
                        next.setHours(next.getHours() + 1, 0, 0, 0);
                    } else {
                        next.setMinutes(nextMinute, 0, 0);
                    }

                    return this.formatDateTime(next);
                }

                // 处理小时间隔 (如 0 */2 * * *)
                if (hour.startsWith('*/') && minute !== '*') {
                    const hourInterval = parseInt(hour.substring(2));
                    const targetMinute = parseInt(minute);
                    const currentHour = now.getHours();
                    let nextHour = Math.ceil((currentHour + 1) / hourInterval) * hourInterval;

                    if (nextHour >= 24) {
                        next.setDate(next.getDate() + 1);
                        nextHour = 0;
                    }

                    next.setHours(nextHour, targetMinute, 0, 0);
                    return this.formatDateTime(next);
                }

                // 处理每小时执行 (如 30 * * * *)
                if (minute !== '*' && hour === '*') {
                    const targetMinute = parseInt(minute);
                    next.setMinutes(targetMinute, 0, 0);

                    // 如果当前时间已经过了这个分钟，设置为下一小时
                    if (next <= now) {
                        next.setHours(next.getHours() + 1);
                    }

                    return this.formatDateTime(next);
                }

                // 处理每天执行 (如 30 14 * * *)
                if (minute !== '*' && hour !== '*' && day === '*' && weekday === '*') {
                    const targetMinute = parseInt(minute);
                    const targetHour = parseInt(hour);

                    next.setHours(targetHour, targetMinute, 0, 0);

                    // 如果今天的时间已经过了，设置为明天
                    if (next <= now) {
                        next.setDate(next.getDate() + 1);
                    }

                    return this.formatDateTime(next);
                }

                // 处理每周执行 (如 0 9 * * 1)
                if (minute !== '*' && hour !== '*' && weekday !== '*' && day === '*') {
                    const targetMinute = parseInt(minute);
                    const targetHour = parseInt(hour);
                    const targetWeekday = parseInt(weekday);

                    next.setHours(targetHour, targetMinute, 0, 0);

                    // 计算到目标星期几的天数
                    const currentWeekday = next.getDay();
                    let daysToAdd = targetWeekday - currentWeekday;

                    if (daysToAdd < 0 || (daysToAdd === 0 && next <= now)) {
                        daysToAdd += 7;
                    }

                    next.setDate(next.getDate() + daysToAdd);
                    return this.formatDateTime(next);
                }

                // 处理每月执行 (如 0 9 15 * *)
                if (minute !== '*' && hour !== '*' && day !== '*' && month === '*') {
                    const targetMinute = parseInt(minute);
                    const targetHour = parseInt(hour);
                    const targetDay = parseInt(day);

                    next.setHours(targetHour, targetMinute, 0, 0);
                    next.setDate(targetDay);

                    // 如果这个月的日期已经过了，设置为下个月
                    if (next <= now) {
                        next.setMonth(next.getMonth() + 1);
                    }

                    return this.formatDateTime(next);
                }

                return null;
            } catch (error) {
                console.error('计算cron时间失败:', error);
                return null;
            }
        },

        isTaskRunning(taskId) {
            return this.runningTasks.has(taskId);
        },

        // 计算任务耗时
        calculateTaskDuration(startTime, endTime) {
            if (!startTime || !endTime) return null;

            const start = new Date(startTime);
            const end = new Date(endTime);
            const durationMs = end - start;

            if (durationMs < 0) return null;

            const seconds = Math.floor(durationMs / 1000);
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;

            if (minutes > 0) {
                return `${minutes}分${remainingSeconds}秒`;
            } else {
                return `${seconds}秒`;
            }
        },

        // 任务日志相关方法
        async viewTaskLogs(task) {
            this.currentTaskLog = task;
            this.showTaskLogModal = true;
            this.taskLogTab = 'output';
            await this.loadTaskLog(task.id);

            // 如果任务正在运行，开始WebSocket实时日志流
            if (this.runningTasks.has(task.id)) {
                this.startTaskLogWebSocket(task.id);
            }
        },

        async loadTaskLog(taskId) {
            this.taskLogLoading = true;
            try {
                // 如果任务正在运行，优先获取运行中的日志
                if (this.runningTasks.has(taskId)) {
                    try {
                        // 先尝试获取运行中的日志
                        const runningResponse = await this.apiRequest(`/api/logs/?task_id=${taskId}&status=running&limit=1`);
                        // 处理分页响应格式
                        let runningLogs;
                        if (runningResponse.items) {
                            runningLogs = runningResponse.items;
                        } else {
                            runningLogs = runningResponse;
                        }
                        if (runningLogs && runningLogs.length > 0) {
                            this.taskLogData = runningLogs[0];
                            // 如果运行中的日志没有输出，显示提示信息
                            if (!this.taskLogData.output) {
                                this.taskLogData.output = '任务正在运行中，等待输出...';
                            }
                            this.taskExecutions[taskId] = this.taskLogData;
                            return;
                        }
                    } catch (error) {
                        console.log('获取运行中日志失败，尝试获取最新日志');
                    }
                }

                // 获取任务最近一次执行记录
                const response = await this.apiRequest(`/api/logs/?task_id=${taskId}&limit=1`);
                // 处理分页响应格式
                let logs;
                if (response.items) {
                    logs = response.items;
                } else {
                    logs = response;
                }
                if (logs && logs.length > 0) {
                    this.taskLogData = logs[0];
                    // 缓存执行记录
                    this.taskExecutions[taskId] = this.taskLogData;
                } else {
                    this.taskLogData = null;
                }
            } catch (error) {
                console.error('加载任务日志失败:', error);
                this.taskLogData = null;
            } finally {
                this.taskLogLoading = false;
            }
        },

        async refreshTaskLog() {
            if (this.currentTaskLog) {
                await this.loadTaskLog(this.currentTaskLog.id);
            }
        },

        // 关闭任务日志模态框
        closeTaskLogModal() {
            this.showTaskLogModal = false;
            this.currentTaskLog = null;
            this.taskLogData = null;
            this.stopRealTimeLogMonitoring();
            this.stopTaskLogWebSocket();
        },

        // 立即运行任务
        async runTask(task) {
            try {
                // 标记为手动运行的任务
                this.manualRunTasks.add(task.id);

                await this.apiRequest(`/api/tasks/${task.id}/run`, {
                    method: 'POST'
                });
                // this.showToast(`任务 ${task.name} 已开始执行`, 'success');

                // 添加到运行中任务集合
                this.runningTasks.add(task.id);

                // 如果日志模态框已打开且是当前任务，启动WebSocket实时日志流
                if (this.showTaskLogModal && this.currentTaskLog && this.currentTaskLog.id === task.id) {
                    // 清空当前日志数据，准备接收新的实时输出
                    this.taskLogData = {
                        id: null,
                        task_id: task.id,
                        task_name: task.name,
                        status: 'running',
                        start_time: new Date().toISOString(),
                        end_time: null,
                        output: '',
                        error_output: '',
                        exit_code: null
                    };
                    // 启动WebSocket实时日志流
                    this.startTaskLogWebSocket(task.id);
                }

                // 刷新任务列表以更新上次运行时间
                setTimeout(() => {
                    this.loadTasks();
                }, 1000);
            } catch (error) {
                console.error('运行任务失败:', error);
                // 如果请求失败，清除手动运行标记
                this.manualRunTasks.delete(task.id);
            }
        },

        // 显示停止任务确认模态框
        showStopTaskModal(task) {
            this.stopTaskTarget = task;
            this.showStopTaskConfirmModal = true;
        },

        // 确认停止任务
        async confirmStopTask() {
            if (!this.stopTaskTarget) return;

            this.stopTaskLoading = true;
            try {
                await this.apiRequest(`/api/tasks/${this.stopTaskTarget.id}/stop`, {
                    method: 'POST'
                });

                this.showToast(`任务 ${this.stopTaskTarget.name} 已发起停止请求`, 'info');
                this.showStopTaskConfirmModal = false;

                // 保存任务ID用于后续检查
                const taskId = this.stopTaskTarget.id;

                // 5秒后检查任务是否停止，如果没有停止则强制停止
                setTimeout(async () => {
                    if (this.runningTasks.has(taskId)) {
                        try {
                            await this.apiRequest(`/api/tasks/${taskId}/stop?force=true`, {
                                method: 'POST'
                            });
                            // 不显示强制停止的toast，让WebSocket消息处理
                        } catch (error) {
                            console.error('强制停止任务失败:', error);
                        }
                    }
                }, 5000);

            } catch (error) {
                console.error('停止任务失败:', error);
                this.showToast('停止任务失败', 'error');
            } finally {
                this.stopTaskLoading = false;
                this.stopTaskTarget = null;
            }
        },

        // 开始实时日志监控
        startRealTimeLogMonitoring(taskId) {
            // 清除之前的定时器
            if (this.logPollingTimer) {
                clearInterval(this.logPollingTimer);
            }

            // 立即加载一次日志
            this.loadTaskLog(taskId);

            // 每1秒轮询一次日志（更频繁的更新）
            this.logPollingTimer = setInterval(async () => {
                if (this.runningTasks.has(taskId) && this.showTaskLogModal && this.currentTaskLog && this.currentTaskLog.id === taskId) {
                    await this.loadTaskLog(taskId);
                } else {
                    // 任务完成或模态框关闭，停止轮询
                    this.stopRealTimeLogMonitoring();
                }
            }, 1000); // 改为1秒轮询一次
        },

        // 停止实时日志监控
        stopRealTimeLogMonitoring() {
            if (this.logPollingTimer) {
                clearInterval(this.logPollingTimer);
                this.logPollingTimer = null;
            }
        },

        // 初始化实时日志显示
        initRealTimeLogDisplay(logId) {
            if (!this.taskLogData) {
                this.taskLogData = {
                    id: logId,
                    task_id: this.currentTaskLog.id,
                    task_name: this.currentTaskLog.name,
                    status: 'running',
                    start_time: new Date().toISOString(),
                    end_time: null,
                    output: '',
                    error_output: '',
                    exit_code: null
                };
            }
        },

        // 处理实时输出
        handleRealTimeOutput(data) {
            // 只处理当前正在查看的任务的输出
            if (!this.currentTaskLog || this.currentTaskLog.id !== data.task_id || !this.showTaskLogModal) {
                return;
            }

            // 确保有日志数据对象
            if (!this.taskLogData) {
                this.initRealTimeLogDisplay(data.log_id);
            }

            // 添加新的输出行
            if (data.output_type === 'stdout') {
                this.taskLogData.output += data.output_line + '\n';
            } else if (data.output_type === 'stderr') {
                this.taskLogData.error_output += data.output_line + '\n';
            }

            // 自动滚动到底部（如果用户没有手动滚动）
            this.$nextTick(() => {
                const outputElement = document.querySelector('.task-log-output');
                if (outputElement) {
                    const isScrolledToBottom = outputElement.scrollHeight - outputElement.clientHeight <= outputElement.scrollTop + 1;
                    if (isScrolledToBottom) {
                        outputElement.scrollTop = outputElement.scrollHeight;
                    }
                }
            });
        },

        // 开始任务日志WebSocket连接
        startTaskLogWebSocket(taskId) {
            // 关闭之前的连接
            if (this.taskLogWs) {
                this.taskLogWs.close();
            }

            // 创建WebSocket连接
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/logs/ws/${taskId}`;
            this.taskLogWs = new WebSocket(wsUrl);

            this.taskLogWs.onopen = () => {
                console.log(`任务日志WebSocket连接已建立，任务ID: ${taskId}`);
                // 重置首次输出标记
                this.hasReceivedFirstOutput = false;
                // 初始化日志数据，如果任务正在运行，清空之前的输出等待历史日志
                if (!this.taskLogData || this.runningTasks.has(taskId)) {
                    this.taskLogData = {
                        id: null,
                        task_id: taskId,
                        task_name: this.currentTaskLog.name,
                        status: 'running',
                        start_time: new Date().toISOString(),
                        end_time: null,
                        output: '',
                        error_output: '',
                        exit_code: null
                    };
                }
            };

            this.taskLogWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    switch (data.type) {

                        case 'task_output':
                            if (data.task_id === taskId && this.taskLogData) {
                                if (data.output_type === 'stdout') {
                                    // 如果是第一行输出且当前有等待提示文本，清空后添加
                                    if (!this.hasReceivedFirstOutput && this.taskLogData.output === '任务正在运行中，等待输出...') {
                                        this.taskLogData.output = data.output_line + '\n';
                                        this.hasReceivedFirstOutput = true;
                                    } else {
                                        // 直接添加输出行和换行符
                                        this.taskLogData.output += data.output_line + '\n';
                                    }
                                } else if (data.output_type === 'stderr') {
                                    this.taskLogData.error_output += data.output_line + '\n';
                                }

                                // 自动滚动到底部
                                this.$nextTick(() => {
                                    const outputElement = document.querySelector('.task-log-output');
                                    if (outputElement) {
                                        outputElement.scrollTop = outputElement.scrollHeight;
                                    }
                                });
                            }
                            break;

                        case 'task_complete':
                            if (data.task_id === taskId) {
                                console.log('任务执行完成');
                                this.runningTasks.delete(taskId);

                                // 不在这里显示toast，由全局WebSocket处理

                                this.taskLogWs.close();
                                this.taskLogWs = null;
                                // 重新加载最终日志
                                setTimeout(() => {
                                    this.loadTaskLog(taskId);
                                }, 1000);
                            }
                            break;

                        case 'task_error':
                            if (data.task_id === taskId) {
                                console.log('任务执行失败');
                                this.runningTasks.delete(taskId);

                                // 不在这里显示toast，由全局WebSocket处理

                                this.taskLogWs.close();
                                this.taskLogWs = null;
                                // 重新加载最终日志
                                setTimeout(() => {
                                    this.loadTaskLog(taskId);
                                }, 1000);
                            }
                            break;
                    }
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };

            this.taskLogWs.onerror = (error) => {
                console.error('任务日志WebSocket连接错误:', error);
            };

            this.taskLogWs.onclose = () => {
                console.log('任务日志WebSocket连接已关闭');
                this.taskLogWs = null;
            };
        },

        // 停止任务日志WebSocket连接
        stopTaskLogWebSocket() {
            if (this.taskLogWs) {
                this.taskLogWs.close();
                this.taskLogWs = null;
            }
        },

        // 文件管理方法
        async loadFiles() {
            this.filesLoading = true;
            try {
                const data = await this.apiRequest(`/api/files/list?path=${this.currentPath}`);
                // 排序：文件夹在前，然后按名称排序
                this.files = data.files.sort((a, b) => {
                    if (a.is_directory && !b.is_directory) return -1;
                    if (!a.is_directory && b.is_directory) return 1;
                    return a.name.localeCompare(b.name);
                });
            } catch (error) {
                console.error('加载文件失败:', error);
                this.files = [];
            } finally {
                this.filesLoading = false;
            }
        },

        handleFileSelect(event) {
            this.selectedFile = event.target.files[0];
        },

        async uploadFile() {
            if (!this.selectedFile) return;

            // 检查Python和Node.js脚本文件名是否包含空格
            const fileName = this.selectedFile.name;
            const fileExt = fileName.toLowerCase().split('.').pop();

            if ((fileExt === 'py' || fileExt === 'js') && fileName.includes(' ')) {
                this.showToast('Python和Node.js脚本文件名不能包含空格，请修改文件名后再上传', 'warning');
                return;
            }

            try {
                const formData = new FormData();
                formData.append('file', this.selectedFile);
                formData.append('path', this.currentPath);

                const response = await fetch('/api/files/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || '上传失败');
                }

                this.showToast('文件上传成功', 'success');
                this.showUploadModal = false;
                this.selectedFile = null;
                await this.loadFiles();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        async createDirectory() {
            try {
                // 验证文件夹名称不能包含空格
                if (this.newDirName.includes(' ')) {
                    this.showToast('文件夹名称不能包含空格', 'error');
                    return;
                }

                const formData = new FormData();
                formData.append('name', this.newDirName);
                formData.append('path', this.currentPath);

                const response = await fetch('/api/files/create-directory', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || '创建目录失败');
                }

                this.showToast('目录创建成功', 'success');
                this.showCreateDirModal = false;
                this.newDirName = '';
                await this.loadFiles();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        async createTextFile() {
            try {
                // 验证文件名
                if (!this.textFileForm.filename.trim()) {
                    this.showToast('请输入文件名', 'error');
                    return;
                }

                // 检查Python和Node.js脚本文件名是否包含空格
                const filename = this.textFileForm.filename.trim();
                const fileExt = filename.toLowerCase().split('.').pop();

                if ((fileExt === 'py' || fileExt === 'js') && filename.includes(' ')) {
                    this.showToast('Python和Node.js脚本文件名不能包含空格，请修改文件名', 'warning');
                    return;
                }

                const response = await fetch('/api/files/create-text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: filename,
                        content: this.textFileForm.content || '',
                        path: this.currentPath
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || '创建文件失败');
                }

                this.showToast('文件创建成功', 'success');
                this.showCreateTextModal = false;
                this.textFileForm.filename = '';
                this.textFileForm.content = '';
                await this.loadFiles();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        enterDirectory(path) {
            this.currentPath = path;
            this.loadFiles();
        },

        downloadFile(path) {
            window.open(`/api/files/download?path=${encodeURIComponent(path)}`, '_blank');
        },

        async deleteFile(file) {
            const type = file.is_directory ? '目录' : '文件';
            if (!confirm(`确定要删除${type} "${file.name}" 吗？`)) return;

            try {
                await this.apiRequest(`/api/files/delete?path=${encodeURIComponent(file.path)}`, {
                    method: 'DELETE'
                });
                this.showToast(`${type}删除成功`, 'success');
                await this.loadFiles();
            } catch (error) {
                console.error('删除文件失败:', error);
            }
        },

        formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // 文件管理新方法
        getFileIcon(filename) {
            const lowerName = filename.toLowerCase();
            const ext = lowerName.split('.').pop();

            // 编程语言文件
            if (ext === 'py') return 'python';
            if (['js', 'jsx', 'ts', 'tsx'].includes(ext)) return 'javascript';
            if (['json', 'yaml', 'yml'].includes(ext)) return 'code';
            if (['html', 'htm', 'xml'].includes(ext)) return 'code';
            if (['css', 'scss', 'sass', 'less'].includes(ext)) return 'code';
            if (['md', 'markdown'].includes(ext)) return 'markdown';
            if (['txt', 'text', 'log', 'logs'].includes(ext)) return 'text';
            if (['ini', 'cfg', 'conf', 'config'].includes(ext)) return 'cog';

            // 压缩文件
            if (this.isArchiveFile(filename)) return 'archive';

            // 其他文本文件
            if (this.isTextFile(filename)) return 'file-alt';

            return 'file';
        },

        isTextFile(filename) {
            const textExtensions = [
                // 编程语言文件
                'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'r', 'sql',
                // 标记语言和配置文件
                'html', 'htm', 'xml', 'xhtml', 'svg', 'css', 'scss', 'sass', 'less', 'json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf', 'config',
                // 文档和文本文件
                'txt', 'text', 'md', 'markdown', 'rst', 'asciidoc', 'org', 'tex', 'rtf',
                // 日志和数据文件
                'log', 'logs', 'out', 'err', 'trace', 'csv', 'tsv', 'dat', 'data',
                // 脚本和批处理文件
                'sh', 'bash', 'zsh', 'fish', 'bat', 'cmd', 'ps1', 'psm1',
                // 其他常见文本格式
                'dockerfile', 'gitignore', 'gitattributes', 'editorconfig', 'env', 'properties', 'makefile', 'cmake', 'gradle',
                // 无扩展名的常见文本文件（通过文件名检测）
            ];

            const lowerName = filename.toLowerCase();
            const ext = lowerName.split('.').pop();

            // 检查扩展名
            if (textExtensions.includes(ext)) {
                return true;
            }

            // 检查无扩展名的常见文本文件
            const textFilenames = [
                'readme', 'license', 'changelog', 'authors', 'contributors', 'copying', 'install', 'news', 'todo',
                'makefile', 'dockerfile', 'vagrantfile', 'gemfile', 'rakefile', 'procfile', 'requirements'
            ];

            const baseFilename = lowerName.split('.')[0];
            return textFilenames.includes(baseFilename) || textFilenames.includes(lowerName);
        },

        isArchiveFile(filename) {
            const archiveExtensions = ['zip', 'gz', 'tgz'];
            const lowerName = filename.toLowerCase();
            return archiveExtensions.some(ext => lowerName.endsWith('.' + ext)) || lowerName.endsWith('.tar.gz');
        },

        getPathParts() {
            return this.currentPath ? this.currentPath.split('/').filter(part => part) : [];
        },

        getPathUpTo(index) {
            const parts = this.getPathParts();
            return parts.slice(0, index + 1).join('/');
        },

        navigateToPath(path) {
            this.currentPath = path;
            this.loadFiles();
        },

        goToParentDirectory() {
            const parts = this.getPathParts();
            if (parts.length > 0) {
                parts.pop();
                this.currentPath = parts.join('/');
                this.loadFiles();
            }
        },

        async previewFile(fileObj) {
            this.currentPreviewFile = fileObj;
            this.previewFileData = fileObj; // 设置previewFileData用于模态框显示
            this.showPreviewModal = true;
            this.previewLoading = true;
            this.previewContent = '';
            this.isEditingFile = false;
            this.editContent = '';

            try {
                const response = await fetch(`/api/files/preview?path=${encodeURIComponent(fileObj.path)}`);
                if (response.ok) {
                    const data = await response.json();
                    this.previewContent = data.content;
                    this.editContent = data.content; // 初始化编辑内容
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '预览失败', 'error');
                    this.closePreviewModal();
                }
            } catch (error) {
                this.showToast('预览文件失败', 'error');
                this.closePreviewModal();
            } finally {
                this.previewLoading = false;
            }
        },

        // 切换编辑模式
        toggleEditMode() {
            this.isEditingFile = !this.isEditingFile;
            if (this.isEditingFile) {
                this.editContent = this.previewContent;
            }
        },

        // 取消编辑
        cancelEdit() {
            this.isEditingFile = false;
            this.editContent = this.previewContent;
        },

        // 关闭预览模态框
        closePreviewModal() {
            this.showPreviewModal = false;
            this.isEditingFile = false;
            this.currentPreviewFile = null;
            this.previewFileData = null; // 清理previewFileData变量
            this.previewContent = '';
            this.editContent = '';
            this.previewLoading = false;
            this.saveLoading = false;
        },

        // 保存文件
        async saveFile() {
            if (!this.currentPreviewFile) return;

            this.saveLoading = true;
            try {
                const response = await fetch('/api/files/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        path: this.currentPreviewFile.path,
                        content: this.editContent
                    })
                });

                if (response.ok) {
                    this.previewContent = this.editContent;
                    this.isEditingFile = false;
                    this.showToast('文件保存成功', 'success');
                    await this.loadFiles(); // 刷新文件列表
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '保存失败', 'error');
                }
            } catch (error) {
                this.showToast('保存文件失败', 'error');
            } finally {
                this.saveLoading = false;
            }
        },

        copyFilePath(path) {
            navigator.clipboard.writeText(path).then(() => {
                this.showToast('文件路径已复制到剪贴板', 'success');
            }).catch(() => {
                this.showToast('复制失败', 'error');
            });
        },

        startRename(file) {
            this.renameForm.file = file;
            this.renameForm.newName = file.name;
            this.showRenameModal = true;
        },

        async confirmRename() {
            // 检查Python和Node.js脚本文件名是否包含空格
            const newName = this.renameForm.newName;
            const fileExt = newName.toLowerCase().split('.').pop();

            if ((fileExt === 'py' || fileExt === 'js') && newName.includes(' ')) {
                this.showToast('Python和Node.js脚本文件名不能包含空格，请修改文件名', 'warning');
                return;
            }

            // 检查文件夹名称是否包含空格
            if (this.renameForm.file.is_directory && newName.includes(' ')) {
                this.showToast('文件夹名称不能包含空格', 'error');
                return;
            }

            try {
                const formData = new FormData();
                formData.append('old_path', this.renameForm.file.path);
                formData.append('new_name', this.renameForm.newName);

                const response = await fetch('/api/files/rename', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    this.showToast('重命名成功', 'success');
                    this.showRenameModal = false;
                    await this.loadFiles();
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '重命名失败', 'error');
                }
            } catch (error) {
                this.showToast('重命名失败', 'error');
            }
        },

        startExtract(file) {
            this.extractForm.file = file;
            this.showExtractModal = true;
        },

        async confirmExtract() {
            if (!this.extractForm.file) return;

            try {
                const formData = new FormData();
                formData.append('path', this.extractForm.file.path);

                const response = await fetch('/api/files/extract', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    this.showToast(result.message, 'success');
                    this.showExtractModal = false;
                    await this.loadFiles();
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '解压失败', 'error');
                }
            } catch (error) {
                this.showToast('解压失败', 'error');
            }
        },

        formatPreviewContent(content) {
            if (!content) return '';
            const lines = content.split('\n');
            const lineNumberWidth = lines.length.toString().length;

            return lines.map((line, index) => {
                const lineNumber = (index + 1).toString().padStart(lineNumberWidth, ' ');
                const escapedLine = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<span style="color: #666; user-select: none; margin-right: 1em;">${lineNumber}</span>${escapedLine}`;
            }).join('\n');
        },

        // 环境变量辅助方法 - 响应式截断长度
        truncateValue(value) {
            if (!value) return '';
            // 在小屏幕上使用更短的长度
            const maxLength = window.innerWidth < 768 ? 10 : 25;
            if (value.length <= maxLength) return value;
            return value.substring(0, maxLength) + '...';
        },

        copyEnvValue(value) {
            navigator.clipboard.writeText(value).then(() => {
                this.showToast('环境变量值已复制到剪贴板', 'success');
            }).catch(() => {
                this.showToast('复制失败', 'error');
            });
        },

        // 日志管理方法
        async loadLogs() {
            this.logsLoading = true;
            try {
                let url = `/api/logs/?limit=${this.logPagination.pageSize}&offset=${(this.logPagination.currentPage - 1) * this.logPagination.pageSize}`;
                if (this.logFilter.taskId) {
                    url += `&task_id=${this.logFilter.taskId}`;
                }
                if (this.logFilter.status) {
                    url += `&status=${this.logFilter.status}`;
                }

                const response = await this.apiRequest(url);

                // 处理分页响应
                if (response.items) {
                    // 新的分页响应格式
                    this.logs = response.items;
                    this.logPagination.total = response.total;
                    this.logPagination.totalPages = response.total_pages;
                } else {
                    // 兼容旧的响应格式
                    this.logs = response;
                    this.logPagination.total = this.logs.length;
                    this.logPagination.totalPages = 1;
                }
            } catch (error) {
                console.error('加载日志失败:', error);
                this.logs = [];
                this.logPagination.total = 0;
                this.logPagination.totalPages = 0;
            } finally {
                this.logsLoading = false;
            }
        },

        // 分页相关方法
        changePage(page) {
            if (page >= 1 && page <= this.logPagination.totalPages) {
                this.logPagination.currentPage = page;
                this.loadLogs();
            }
        },

        getPageNumbers() {
            const pages = [];
            const current = this.logPagination.currentPage;
            const total = this.logPagination.totalPages;

            // 显示当前页前后2页
            const start = Math.max(1, current - 2);
            const end = Math.min(total, current + 2);

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            return pages;
        },

        // 删除筛选结果
        async deleteFilteredLogs() {
            if (!confirm('确定要删除当前筛选的日志吗？')) return;

            try {
                let url = '/api/logs/';
                const params = [];
                if (this.logFilter.taskId) {
                    params.push(`task_id=${this.logFilter.taskId}`);
                }
                if (this.logFilter.status) {
                    params.push(`status=${this.logFilter.status}`);
                }
                if (params.length > 0) {
                    url += '?' + params.join('&');
                }

                await this.apiRequest(url, {
                    method: 'DELETE'
                });
                this.showToast('筛选日志已删除', 'success');
                this.logPagination.currentPage = 1; // 重置到第一页
                await this.loadLogs();
            } catch (error) {
                console.error('删除筛选日志失败:', error);
            }
        },

        // 删除单条日志
        async deleteLog(logId) {
            if (!confirm('确定要删除这条日志吗？')) return;

            try {
                await this.apiRequest(`/api/logs/${logId}`, {
                    method: 'DELETE'
                });
                this.showToast('日志已删除', 'success');
                await this.loadLogs();
            } catch (error) {
                console.error('删除日志失败:', error);
            }
        },

        // 清空所有日志（系统设置页面）
        async clearAllLogs() {
            if (!confirm('确定要清空所有日志吗？此操作不可恢复！')) return;

            try {
                const result = await this.apiRequest('/api/settings/clear-all-logs', {
                    method: 'POST'
                });
                this.showToast(result.message || '所有日志已清空', 'success');
                if (this.currentPage === 'logs') {
                    this.logPagination.currentPage = 1;
                    await this.loadLogs();
                }
            } catch (error) {
                console.error('清空所有日志失败:', error);
            }
        },

        // 保存日志清理设置
        async saveLogCleanupSettings() {
            try {
                await this.apiRequest('/api/settings/log-cleanup', {
                    method: 'POST',
                    body: JSON.stringify(this.logCleanupSettings)
                });
                this.showToast('日志清理设置已保存', 'success');
            } catch (error) {
                console.error('保存日志清理设置失败:', error);
            }
        },

        // 加载日志清理设置
        async loadLogCleanupSettings() {
            try {
                const settings = await this.apiRequest('/api/settings/log-cleanup');
                this.logCleanupSettings = { ...this.logCleanupSettings, ...settings };
            } catch (error) {
                console.error('加载日志清理设置失败:', error);
            }
        },

        // 加载命令配置
        async loadCommandConfig() {
            try {
                const config = await this.apiRequest('/api/settings/command-config');
                this.commandConfig = { ...this.commandConfig, ...config };
                // 保存原始配置用于后续比较
                this.originalCommandConfig = { ...this.commandConfig };
            } catch (error) {
                console.error('加载命令配置失败:', error);
                // 使用默认配置
                this.commandConfig = {
                    python_command: 'python',
                    nodejs_command: 'node',
                    python_package_manager: 'pip',
                    nodejs_package_manager: 'npm'
                };
                // 保存原始配置用于后续比较
                this.originalCommandConfig = { ...this.commandConfig };
            }
        },

        // 测试命令
        async testCommand(type) {
            if (this.isTestingCommand) return;

            this.isTestingCommand = true;
            this.commandTestResult[type] = null;

            try {
                const command = type === 'python' ? this.commandConfig.python_command : this.commandConfig.nodejs_command;
                const response = await fetch('/api/settings/test-command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        command_type: type,
                        command: command
                    })
                });

                const result = await response.json();
                this.commandTestResult[type] = result;

                if (result.success) {
                    this.showToast(`${type === 'python' ? 'Python' : 'Node.js'}命令测试成功`, 'success');
                } else {
                    this.showToast(`${type === 'python' ? 'Python' : 'Node.js'}命令测试失败`, 'error');
                }
            } catch (error) {
                console.error('测试命令失败:', error);
                this.commandTestResult[type] = {
                    success: false,
                    message: '测试失败：网络错误'
                };
                this.showToast('命令测试失败', 'error');
            } finally {
                this.isTestingCommand = false;
            }
        },

        // 测试包管理器
        async testPackageManager(type) {
            if (this.isTestingPackageManager) return;

            this.isTestingPackageManager = true;
            this.packageManagerTestResult[type] = null;

            try {
                const manager = type === 'python' ? this.commandConfig.python_package_manager : this.commandConfig.nodejs_package_manager;
                const response = await fetch('/api/settings/test-package-manager', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        manager_type: type,
                        manager: manager
                    })
                });

                const result = await response.json();
                this.packageManagerTestResult[type] = result;

                if (result.success) {
                    this.showToast(`${manager}包管理器测试成功`, 'success');
                } else {
                    this.showToast(`${manager}包管理器测试失败`, 'error');
                }
            } catch (error) {
                console.error('测试包管理器失败:', error);
                this.packageManagerTestResult[type] = {
                    success: false,
                    message: '测试失败：网络错误'
                };
                this.showToast('包管理器测试失败', 'error');
            } finally {
                this.isTestingPackageManager = false;
            }
        },

        // 保存命令配置
        async saveCommandConfig() {
            if (this.isSavingCommandConfig) return;

            // 验证配置是否可以保存
            const validationResult = this.validateCommandConfig();
            if (!validationResult.valid) {
                this.showToast(validationResult.message, 'error');
                return;
            }

            this.isSavingCommandConfig = true;

            try {
                await this.apiRequest('/api/settings/command-config', {
                    method: 'POST',
                    body: JSON.stringify(this.commandConfig)
                });

                // 保存成功后，更新原始配置用于后续比较
                this.originalCommandConfig = { ...this.commandConfig };
                // 清空测试结果
                this.commandTestResult = { python: null, nodejs: null };
                this.packageManagerTestResult = { python: null, nodejs: null };

                this.showToast('命令配置保存成功', 'success');
            } catch (error) {
                console.error('保存命令配置失败:', error);
                this.showToast('保存命令配置失败', 'error');
            } finally {
                this.isSavingCommandConfig = false;
            }
        },

        // 验证命令配置是否可以保存
        validateCommandConfig() {
            if (!this.originalCommandConfig) {
                // 如果没有原始配置，说明是首次加载，需要测试所有配置
                return {
                    valid: false,
                    message: '请先测试所有命令和包管理器配置'
                };
            }

            // 检查Python执行命令是否需要测试
            const pythonCommandChanged = this.commandConfig.python_command !== this.originalCommandConfig.python_command;
            if (pythonCommandChanged && (!this.commandTestResult.python || !this.commandTestResult.python.success)) {
                return {
                    valid: false,
                    message: 'Python执行命令已修改，请先测试'
                };
            }

            // 检查Node.js执行命令是否需要测试
            const nodejsCommandChanged = this.commandConfig.nodejs_command !== this.originalCommandConfig.nodejs_command;
            if (nodejsCommandChanged && (!this.commandTestResult.nodejs || !this.commandTestResult.nodejs.success)) {
                return {
                    valid: false,
                    message: 'Node.js执行命令已修改，请先测试'
                };
            }

            // 检查Python包管理器是否需要测试
            const pythonManagerChanged = this.commandConfig.python_package_manager !== this.originalCommandConfig.python_package_manager;
            if (pythonManagerChanged && (!this.packageManagerTestResult.python || !this.packageManagerTestResult.python.success)) {
                return {
                    valid: false,
                    message: 'Python包管理器已修改，请先测试'
                };
            }

            // 检查Node.js包管理器是否需要测试
            const nodejsManagerChanged = this.commandConfig.nodejs_package_manager !== this.originalCommandConfig.nodejs_package_manager;
            if (nodejsManagerChanged && (!this.packageManagerTestResult.nodejs || !this.packageManagerTestResult.nodejs.success)) {
                return {
                    valid: false,
                    message: 'Node.js包管理器已修改，请先测试'
                };
            }

            return { valid: true };
        },

        // 环境变量管理方法
        async loadEnvVars() {
            this.envVarsLoading = true;
            try {
                this.envVars = await this.apiRequest('/api/env/');
            } catch (error) {
                console.error('加载环境变量失败:', error);
                this.envVars = [];
            } finally {
                this.envVarsLoading = false;
            }
        },

        resetEnvForm() {
            this.envForm = {
                key: '',
                value: '',
                description: ''
            };
        },

        editEnv(env) {
            this.editingEnv = env;
            this.envForm = { ...env };
            this.showEnvModal = true;
        },

        async saveEnv() {
            // 验证变量名不能以数字开头
            if (/^\d/.test(this.envForm.key)) {
                this.showToast('变量名不能以数字开头', 'error');
                return;
            }

            // 验证变量名只能包含字母、数字和下划线
            if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(this.envForm.key)) {
                this.showToast('变量名只能包含字母、数字和下划线，且不能以数字开头', 'error');
                return;
            }

            try {
                if (this.editingEnv) {
                    await this.apiRequest(`/api/env/${this.editingEnv.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(this.envForm)
                    });
                    this.showToast('环境变量更新成功', 'success');
                } else {
                    await this.apiRequest('/api/env/', {
                        method: 'POST',
                        body: JSON.stringify(this.envForm)
                    });
                    this.showToast('环境变量创建成功', 'success');
                }
                this.showEnvModal = false;
                await this.loadEnvVars();
            } catch (error) {
                console.error('保存环境变量失败:', error);
            }
        },

        async deleteEnv(env) {
            if (!confirm(`确定要删除环境变量 "${env.key}" 吗？`)) return;

            try {
                await this.apiRequest(`/api/env/${env.id}`, {
                    method: 'DELETE'
                });
                this.showToast('环境变量删除成功', 'success');
                await this.loadEnvVars();
            } catch (error) {
                console.error('删除环境变量失败:', error);
            }
        },

        // 包管理方法
        async loadPackages() {
            this.packagesLoading = true;
            try {
                const [pythonResponse, nodejsResponse] = await Promise.all([
                    fetch('/api/packages/python/list'),
                    fetch('/api/packages/nodejs/list')
                ]);

                if (pythonResponse.ok) {
                    this.pythonPackages = await pythonResponse.json();
                } else {
                    this.pythonPackages = [];
                }

                if (nodejsResponse.ok) {
                    this.nodejsPackages = await nodejsResponse.json();
                } else {
                    this.nodejsPackages = [];
                }

                // 初始化过滤列表
                this.filterPackages();
            } catch (error) {
                console.error('加载包列表失败:', error);
                this.pythonPackages = [];
                this.nodejsPackages = [];
                this.filteredPythonPackages = [];
                this.filteredNodejsPackages = [];
            } finally {
                this.packagesLoading = false;
            }
        },

        // 过滤包列表
        filterPackages() {
            const query = this.packageSearchQuery.toLowerCase().trim();

            if (!query) {
                this.filteredPythonPackages = [...this.pythonPackages];
                this.filteredNodejsPackages = [...this.nodejsPackages];
            } else {
                this.filteredPythonPackages = this.pythonPackages.filter(pkg =>
                    pkg.name.toLowerCase().includes(query)
                );
                this.filteredNodejsPackages = this.nodejsPackages.filter(pkg =>
                    pkg.name.toLowerCase().includes(query)
                );
            }
        },

        async installPackage() {
            // 检查环境
            if (this.environmentCheck) {
                if (this.packageForm.package_type === 'python' && !this.environmentCheck.python.installed) {
                    this.showToast('缺失Python环境，无法安装Python包。请先安装Python环境。', 'error');
                    return;
                }
                if (this.packageForm.package_type === 'nodejs' && !this.environmentCheck.nodejs.installed) {
                    this.showToast('缺失Node.js环境，无法安装Node.js包。请先安装Node.js环境。', 'error');
                    return;
                }
            }

            try {
                // 初始化安装日志模态框
                this.packageInstallStatus = 'installing';
                this.packageOperationType = 'install';
                this.packageInstallLogs = [];
                this.packageInstallInfo = {
                    type: this.packageForm.package_type,
                    name: this.packageForm.package_name,
                    version: this.packageForm.version || ''
                };

                // 关闭安装表单模态框，显示日志模态框
                this.showPackageModal = false;
                this.showPackageInstallModal = true;

                // 发送安装请求
                await this.apiRequest('/api/packages/install', {
                    method: 'POST',
                    body: JSON.stringify(this.packageForm)
                });

                // 重置表单
                this.packageForm = {
                    package_type: 'python',
                    package_name: '',
                    version: ''
                };
            } catch (error) {
                console.error('安装包失败:', error);
                this.packageInstallStatus = 'failed';
                this.addPackageInstallLog('✗ 安装请求失败: ' + error.message);
            }
        },

        // 添加包安装日志
        addPackageInstallLog(message) {
            this.packageInstallLogs.push({
                id: ++this.packageLogId,
                message: message,
                timestamp: new Date().toLocaleTimeString()
            });

            // 自动滚动到底部
            setTimeout(() => {
                const container = document.querySelector('[x-ref="packageLogContainer"]');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }, 0);
        },

        // 清空包安装日志
        clearPackageInstallLogs() {
            this.packageInstallLogs = [];
        },

        // 关闭包安装日志模态框
        closePackageInstallModal() {
            if (this.packageInstallStatus === 'installing') {
                if (!confirm('安装正在进行中，确定要关闭吗？')) {
                    return;
                }
            }
            this.showPackageInstallModal = false;
            this.packageInstallStatus = 'idle';
            this.packageInstallLogs = [];
        },

        async uninstallPackage(packageType, packageName) {
            if (!confirm(`确定要卸载包 "${packageName}" 吗？`)) return;

            try {
                // 初始化卸载日志模态框
                this.packageInstallStatus = 'installing'; // 复用安装状态
                this.packageOperationType = 'uninstall';
                this.packageInstallLogs = [];
                this.packageInstallInfo = {
                    type: packageType,
                    name: packageName,
                    version: ''
                };

                // 显示日志模态框
                this.showPackageInstallModal = true;

                // 发送卸载请求
                await this.apiRequest(`/api/packages/uninstall?package_type=${packageType}&package_name=${packageName}`, {
                    method: 'DELETE'
                });
            } catch (error) {
                console.error('卸载包失败:', error);
                this.packageInstallStatus = 'failed';
                this.addPackageInstallLog('✗ 卸载请求失败: ' + error.message);
            }
        },

        // 系统设置方法
        async loadSystemInfo() {
            this.systemInfoLoading = true;
            try {
                this.systemInfo = await this.apiRequest('/api/settings/system-info');
                // 同时加载时区配置
                await this.loadTimezoneConfig();
            } catch (error) {
                console.error('加载系统信息失败:', error);
            } finally {
                this.systemInfoLoading = false;
            }
        },

        // 配色方案管理方法
        async loadColorScheme() {
            try {
                const response = await fetch('/api/settings/color-scheme');
                if (response.ok) {
                    const data = await response.json();
                    this.currentColorScheme = data.color_scheme;
                    this.applyColorScheme(data.color_scheme);
                } else {
                    // 如果API调用失败（如未登录），使用默认配色方案
                    console.log('未登录，使用默认配色方案');
                    this.currentColorScheme = 'blue';
                    this.applyColorScheme('blue');
                }
            } catch (error) {
                console.error('加载配色方案失败:', error);
                // 使用默认配色方案
                this.currentColorScheme = 'blue';
                this.applyColorScheme('blue');
            }
        },

        async updateColorScheme(schemeId) {
            try {
                await this.apiRequest('/api/settings/color-scheme', {
                    method: 'POST',
                    body: JSON.stringify({ color_scheme: schemeId })
                });
                this.currentColorScheme = schemeId;
                this.applyColorScheme(schemeId);
                this.showToast('配色方案更新成功', 'success');
            } catch (error) {
                console.error('更新配色方案失败:', error);
            }
        },

        applyColorScheme(schemeId) {
            // 移除所有配色方案类
            document.body.classList.remove('theme-blue', 'theme-green', 'theme-purple', 'theme-gray', 'theme-orange', 'theme-dark');
            // 应用新的配色方案类
            document.body.classList.add(`theme-${schemeId}`);
            // 更新当前配色方案
            this.currentColorScheme = schemeId;
        },

        getColorSchemeInfo(schemeId) {
            return this.colorSchemes.find(scheme => scheme.id === schemeId) || this.colorSchemes[0];
        },

        // 格式化预览内容，添加行号和分隔线
        formatPreviewContent(content) {
            if (!content) return '';

            const lines = content.split('\n');
            const maxLineNumber = lines.length;
            const lineNumberWidth = Math.max(maxLineNumber.toString().length, 2);

            return lines.map((line, index) => {
                const lineNumber = (index + 1).toString().padStart(lineNumberWidth, ' ');
                const escapedLine = line
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');

                return `<span class="line-number">${lineNumber}</span><span class="line-separator">│</span><span class="line-content">${escapedLine}</span>`;
            }).join('\n');
        },

        async changeUsername() {
            try {
                await this.apiRequest('/api/settings/change-username', {
                    method: 'POST',
                    body: JSON.stringify(this.usernameForm)
                });
                this.showToast('用户名修改成功', 'success');
                this.showChangeUsernameModal = false;
                this.usernameForm = { new_username: '', password: '' };
                // 重新获取用户信息
                await this.checkAuth();
            } catch (error) {
                console.error('修改用户名失败:', error);
            }
        },

        async changePassword() {
            if (this.passwordForm.new_password !== this.passwordForm.confirm_password) {
                this.showToast('新密码和确认密码不匹配', 'error');
                return;
            }

            try {
                await this.apiRequest('/api/settings/change-password', {
                    method: 'POST',
                    body: JSON.stringify({
                        old_password: this.passwordForm.old_password,
                        new_password: this.passwordForm.new_password
                    })
                });
                this.showToast('密码修改成功', 'success');
                this.showChangePasswordModal = false;
                this.passwordForm = { old_password: '', new_password: '', confirm_password: '' };
            } catch (error) {
                console.error('修改密码失败:', error);
            }
        },

        // 页面切换时加载数据
        async switchPage(page) {
            this.currentPage = page;
            this.mobileMenuOpen = false; // 关闭移动端菜单

            switch (page) {
                case 'tasks':
                    if (!this.dataLoaded.tasks) {
                        await this.loadTasks();
                        this.dataLoaded.tasks = true;
                    }
                    break;
                case 'files':
                    if (!this.dataLoaded.files) {
                        await this.loadFiles();
                        this.dataLoaded.files = true;
                    }
                    break;
                case 'logs':
                    if (!this.dataLoaded.logs) {
                        await this.loadLogs();
                        this.dataLoaded.logs = true;
                    }
                    break;
                case 'env':
                    if (!this.dataLoaded.envVars) {
                        await this.loadEnvVars();
                        this.dataLoaded.envVars = true;
                    }
                    break;
                case 'packages':
                    if (!this.dataLoaded.packages) {
                        await this.loadPackages();
                        this.dataLoaded.packages = true;
                    }
                    await this.checkEnvironment(); // 确保环境检测信息是最新的
                    await this.loadPackageManagerConfig(); // 加载包管理器配置
                    break;
                case 'notifications':
                    // 确保任务数据已加载，通知配置依赖任务数据
                    if (!this.dataLoaded.tasks) {
                        await this.loadTasks();
                        this.dataLoaded.tasks = true;
                    }
                    if (!this.dataLoaded.notifications) {
                        await this.loadNotificationConfigs();
                        this.dataLoaded.notifications = true;
                    }
                    break;
                case 'api-debug':
                    if (!this.dataLoaded.debugConfigs) {
                        await this.loadDebugConfigs();
                        this.dataLoaded.debugConfigs = true;
                    }
                    if (!this.dataLoaded.notifications) {
                        await this.loadNotificationConfigs(); // 加载通知配置供选择
                        this.dataLoaded.notifications = true;
                    }
                    await this.loadAvailableVariables();
                    await this.checkVersionUpdate(); // 加载版本信息用于User-Agent
                    this.updateUserAgent(); // 更新User-Agent头的值
                    break;
                case 'subscriptions':
                    if (!this.dataLoaded.subscriptions) {
                        await this.loadSubscriptions();
                        this.dataLoaded.subscriptions = true;
                    }
                    // 确保通知配置已加载，订阅页面需要用到
                    if (!this.dataLoaded.notifications) {
                        await this.loadNotificationConfigs();
                        this.dataLoaded.notifications = true;
                    }
                    break;
                case 'settings':
                    if (!this.dataLoaded.systemInfo) {
                        await this.loadSystemInfo();
                        this.dataLoaded.systemInfo = true;
                    }
                    // 确保通知配置已加载，多因素认证需要用到
                    if (!this.dataLoaded.notifications) {
                        await this.loadNotificationConfigs();
                        this.dataLoaded.notifications = true;
                    }
                    await this.loadColorScheme();
                    await this.loadLogCleanupSettings();
                    await this.loadCommandConfig(); // 加载命令配置
                    await this.loadSecurityConfig();
                    await this.checkVersionUpdate(); // 加载版本升级信息
                    break;
            }
        },

        // 通知服务相关方法
        async loadNotificationConfigs() {
            this.notificationConfigsLoading = true;
            try {
                this.notificationConfigs = await this.apiRequest('/api/notifications/configs');
                await this.loadActiveNotificationConfigs();
                await this.loadTaskNotificationConfigs();
                await this.loadSendNotifyConfig();
            } catch (error) {
                console.error('加载通知配置失败:', error);
                this.notificationConfigs = [];
            } finally {
                this.notificationConfigsLoading = false;
            }
        },

        async loadActiveNotificationConfigs() {
            try {
                this.activeNotificationConfigs = await this.apiRequest('/api/notifications/active-configs');
            } catch (error) {
                console.error('加载激活的通知配置失败:', error);
                this.activeNotificationConfigs = [];
            }
        },

        async loadTaskNotificationConfigs() {
            try {
                const configs = await this.apiRequest('/api/notifications/task-configs');
                this.taskNotificationConfigs = {};
                configs.forEach(config => {
                    this.taskNotificationConfigs[config.task_id] = {
                        notification_type: config.notification_type || '',
                        error_only: config.error_only || false,
                        keywords: config.keywords || ''
                    };
                });

                // 确保任务数据已加载
                if (this.tasks.length === 0) {
                    await this.loadTasks();
                }

                // 为没有配置的任务初始化默认配置
                this.tasks.forEach(task => {
                    if (!this.taskNotificationConfigs[task.id]) {
                        this.taskNotificationConfigs[task.id] = {
                            notification_type: '',
                            error_only: false,
                            keywords: ''
                        };
                    }
                });
            } catch (error) {
                console.error('加载任务通知配置失败:', error);
                this.taskNotificationConfigs = {};
            }
        },

        getNotificationDisplayName(name) {
            const displayNames = {
                'email': '邮箱通知',
                'pushplus': 'PushPlus',
                'wxpusher': 'WxPusher',
                'telegram': 'Telegram机器人',
                'wecom': '企业微信',
                'serverchan': 'Server酱',
                'dingtalk': '钉钉机器人',
                'bark': 'Bark'
            };
            return displayNames[name] || name;
        },

        // 获取带账户信息的通知显示名称
        getNotificationDisplayNameWithAccount(config) {
            const baseName = this.getNotificationDisplayName(config.name);

            if (!config.config) {
                return baseName;
            }

            let accountInfo = '';

            switch (config.name) {
                case 'pushplus':
                    if (config.config.token) {
                        const token = config.config.token;
                        const maskedToken = token.substring(0, 4) + '******' + token.substring(token.length - 4);
                        accountInfo = `（${maskedToken}）`;
                    }
                    break;
                case 'wxpusher':
                    if (config.config.app_token) {
                        const token = config.config.app_token;
                        const maskedToken = token.substring(0, 6) + '******' + token.substring(token.length - 6);
                        accountInfo = `（${maskedToken}）`;
                    }
                    break;
                case 'email':
                    if (config.config.to_email) {
                        accountInfo = `（${config.config.to_email}）`;
                    }
                    break;
                case 'telegram':
                    if (config.config.bot_token) {
                        const token = config.config.bot_token;
                        const maskedToken = token.substring(0, 6) + '******' + token.substring(token.length - 6);
                        accountInfo = `（${maskedToken}）`;
                    } else if (config.config.chat_id) {
                        const chatId = config.config.chat_id.toString();
                        const maskedChatId = chatId.substring(0, 3) + '******' + chatId.substring(chatId.length - 3);
                        accountInfo = `（${maskedChatId}）`;
                    }
                    break;
                case 'wecom':
                    if (config.config.webhook_url) {
                        try {
                            const url = new URL(config.config.webhook_url);
                            const params = new URLSearchParams(url.search);
                            const key = params.get('key');
                            if (key) {
                                const maskedKey = key.substring(0, 6) + '******' + key.substring(key.length - 6);
                                accountInfo = `（${maskedKey}）`;
                            } else {
                                const maskedUrl = config.config.webhook_url.substring(0, 30) + '...';
                                accountInfo = `（${maskedUrl}）`;
                            }
                        } catch (e) {
                            const maskedUrl = config.config.webhook_url.substring(0, 30) + '...';
                            accountInfo = `（${maskedUrl}）`;
                        }
                    }
                    break;
                case 'serverchan':
                    if (config.config.send_key) {
                        const key = config.config.send_key;
                        const maskedKey = key.substring(0, 4) + '******' + key.substring(key.length - 4);
                        accountInfo = `（${maskedKey}）`;
                    }
                    break;
                case 'dingtalk':
                    if (config.config.webhook_url) {
                        try {
                            const url = new URL(config.config.webhook_url);
                            const params = new URLSearchParams(url.search);
                            const accessToken = params.get('access_token');
                            if (accessToken) {
                                const maskedToken = accessToken.substring(0, 6) + '******' + accessToken.substring(accessToken.length - 6);
                                accountInfo = `（${maskedToken}）`;
                            } else {
                                const maskedUrl = config.config.webhook_url.substring(0, 30) + '...';
                                accountInfo = `（${maskedUrl}）`;
                            }
                        } catch (e) {
                            const maskedUrl = config.config.webhook_url.substring(0, 30) + '...';
                            accountInfo = `（${maskedUrl}）`;
                        }
                    }
                    break;
                case 'bark':
                    if (config.config.device_key) {
                        const key = config.config.device_key;
                        const maskedKey = key.substring(0, 4) + '******' + key.substring(key.length - 4);
                        accountInfo = `（${maskedKey}）`;
                    }
                    break;
            }

            return baseName + accountInfo;
        },

        // 检查任务是否有通知配置
        hasNotificationConfig(taskId) {
            const config = this.taskNotificationConfigs[taskId];
            return config && config.notification_type && config.notification_type !== '';
        },

        // 更新任务通知指示器
        updateTaskNotificationIndicator(taskId) {
            // 确保任务通知配置对象存在
            if (!this.taskNotificationConfigs[taskId]) {
                this.taskNotificationConfigs[taskId] = {
                    notification_type: '',
                    error_only: false,
                    keywords: ''
                };
            }
        },

        getTaskNotificationConfig(taskId) {
            return this.taskNotificationConfigs[taskId] || {
                notification_type: '',
                error_only: false,
                keywords: ''
            };
        },

        resetNotificationConfigForm() {
            this.notificationConfigForm = {
                name: '',
                config: {}
            };
        },

        editNotificationConfig(config) {
            this.editingNotificationConfig = config;
            this.notificationConfigForm = {
                name: config.name,
                config: { ...config.config }
            };

            // 如果是WxPusher配置，将uids数组转换为文本
            if (config.name === 'wxpusher' && config.config.uids) {
                this.notificationConfigForm.config.uids_text = Array.isArray(config.config.uids)
                    ? config.config.uids.join('\n')
                    : config.config.uids;
            }

            this.showNotificationConfigModal = true;
        },

        async saveNotificationConfig() {
            try {
                // 处理WxPusher的UID文本转换为数组
                const configData = { ...this.notificationConfigForm };
                if (configData.name === 'wxpusher' && configData.config.uids_text) {
                    // 将文本转换为UID数组
                    const uids = configData.config.uids_text
                        .split(/[,\n]/)
                        .map(uid => uid.trim())
                        .filter(uid => uid.length > 0);
                    configData.config.uids = uids;
                    delete configData.config.uids_text;
                }

                if (this.editingNotificationConfig) {
                    await this.apiRequest(`/api/notifications/configs/${this.editingNotificationConfig.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(configData)
                    });
                    this.showToast('通知配置更新成功', 'success');
                } else {
                    await this.apiRequest('/api/notifications/configs', {
                        method: 'POST',
                        body: JSON.stringify(configData)
                    });
                    this.showToast('通知配置创建成功', 'success');
                }
                this.showNotificationConfigModal = false;
                this.editingNotificationConfig = null;
                this.resetNotificationConfigForm();
                await this.loadNotificationConfigs();
            } catch (error) {
                console.error('保存通知配置失败:', error);
            }
        },

        // 判断通知配置是否正在测试
        isTestingNotification(configId) {
            return this.testingNotifications.has(configId);
        },

        async testNotification(configId) {
            // 如果已经在测试中，直接返回
            if (this.testingNotifications.has(configId)) {
                return;
            }

            // 添加到测试中的集合
            this.testingNotifications.add(configId);

            try {
                const result = await this.apiRequest('/api/notifications/test', {
                    method: 'POST',
                    body: JSON.stringify({ config_id: configId })
                });
                this.showToast(result.message, 'success');
                await this.loadNotificationConfigs();
            } catch (error) {
                console.error('测试通知失败:', error);
                // 显示错误toast
                const errorMessage = error.message || '测试通知失败';
                this.showToast(errorMessage, 'error');
            } finally {
                // 从测试中的集合移除
                this.testingNotifications.delete(configId);
            }
        },

        async deleteNotificationConfig(configId) {
            if (!confirm('确定要删除这个通知配置吗？')) return;

            try {
                await this.apiRequest(`/api/notifications/configs/${configId}`, {
                    method: 'DELETE'
                });
                this.showToast('通知配置删除成功', 'success');
                await this.loadNotificationConfigs();
            } catch (error) {
                console.error('删除通知配置失败:', error);
            }
        },

        async saveTaskNotificationConfig(taskId) {
            try {
                const config = this.taskNotificationConfigs[taskId] || {
                    notification_type: '',
                    error_only: false,
                    keywords: ''
                };

                const requestData = {
                    task_id: parseInt(taskId),
                    notification_type: config.notification_type || null,
                    error_only: Boolean(config.error_only),
                    keywords: config.keywords || null
                };

                // console.log('保存任务通知配置 - 原始配置:', config);
                // console.log('保存任务通知配置 - 请求数据:', requestData);
                // console.log('保存任务通知配置 - taskId类型:', typeof taskId, taskId);

                await this.apiRequest('/api/notifications/task-configs', {
                    method: 'POST',
                    body: JSON.stringify(requestData)
                });
                this.showToast('任务通知配置保存成功', 'success');
                await this.loadTaskNotificationConfigs();
            } catch (error) {
                console.error('保存任务通知配置失败:', error);
            }
        },

        // SendNotify配置相关方法
        async loadSendNotifyConfig() {
            this.sendNotifyConfigLoading = true;
            try {
                const config = await this.apiRequest('/api/notifications/sendnotify-config');
                this.sendNotifyConfig = {
                    notification_type: config.notification_type || ''
                };
            } catch (error) {
                console.error('加载SendNotify配置失败:', error);
                this.sendNotifyConfig = {
                    notification_type: ''
                };
            } finally {
                this.sendNotifyConfigLoading = false;
            }
        },

        async saveSendNotifyConfig() {
            this.sendNotifyConfigSaving = true;
            try {
                const result = await this.apiRequest('/api/notifications/sendnotify-config', {
                    method: 'POST',
                    body: JSON.stringify({
                        notification_type: this.sendNotifyConfig.notification_type || null
                    })
                });
                this.showToast(result.message || 'SendNotify配置保存成功', 'success');
            } catch (error) {
                console.error('保存SendNotify配置失败:', error);
                this.showToast('保存SendNotify配置失败', 'error');
            } finally {
                this.sendNotifyConfigSaving = false;
            }
        },

        // Cron表达式生成器相关方法
        resetCronForm() {
            this.cronForm = {
                minute: '*',
                hour: '*',
                day: '*',
                month: '*',
                weekday: '*'
            };
            this.generatedCron = '* * * * *';
        },

        updateCronExpression() {
            this.generatedCron = `${this.cronForm.minute} ${this.cronForm.hour} ${this.cronForm.day} ${this.cronForm.month} ${this.cronForm.weekday}`;
        },

        applyCronTemplate(cronExpression) {
            const parts = cronExpression.split(' ');
            if (parts.length === 5) {
                this.cronForm.minute = parts[0];
                this.cronForm.hour = parts[1];
                this.cronForm.day = parts[2];
                this.cronForm.month = parts[3];
                this.cronForm.weekday = parts[4];
                this.generatedCron = cronExpression;
            }
        },

        applyCronExpression() {
            this.taskForm.cron_expression = this.generatedCron;
            this.showCronGeneratorModal = false;
            this.showToast('Cron表达式已应用', 'success');
        },

        getCronDescription(cronExpression) {
            if (!cronExpression) return '';

            // 使用现有的getTaskNextRunTime逻辑来生成描述
            const tempTask = { cron_expression: cronExpression, is_active: true };
            const description = this.getTaskNextRunTime(tempTask);

            if (description === '根据计划执行' || description === '表达式解析错误') {
                return this.getDetailedCronDescription(cronExpression);
            }

            return description;
        },

        getDetailedCronDescription(cronExpression) {
            const parts = cronExpression.split(' ');
            if (parts.length !== 5) return '无效的Cron表达式';

            const [minute, hour, day, month, weekday] = parts;
            let description = '执行时间: ';

            // 分析各个部分
            const minuteDesc = this.describeCronPart(minute, 'minute');
            const hourDesc = this.describeCronPart(hour, 'hour');
            const dayDesc = this.describeCronPart(day, 'day');
            const monthDesc = this.describeCronPart(month, 'month');
            const weekdayDesc = this.describeCronPart(weekday, 'weekday');

            // 组合描述
            if (weekday !== '*') {
                description += weekdayDesc;
            } else if (day !== '*') {
                description += `每月${day}日`;
            } else {
                description += '每天';
            }

            if (hour !== '*') {
                description += ` ${hourDesc}`;
            }

            if (minute !== '*') {
                description += ` ${minuteDesc}`;
            }

            return description;
        },

        describeCronPart(part, type) {
            if (part === '*') {
                return type === 'minute' ? '每分钟' :
                       type === 'hour' ? '每小时' :
                       type === 'day' ? '每天' :
                       type === 'month' ? '每月' : '每天';
            }

            if (part.startsWith('*/')) {
                const interval = part.substring(2);
                return type === 'minute' ? `每${interval}分钟` :
                       type === 'hour' ? `每${interval}小时` :
                       `每${interval}${type === 'day' ? '天' : type === 'month' ? '月' : ''}`;
            }

            if (type === 'minute') {
                return `${part}分`;
            } else if (type === 'hour') {
                return `${part}时`;
            } else if (type === 'weekday') {
                const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                return weekdays[parseInt(part)] || `周${part}`;
            }

            return part;
        },

        // 获取运行中的任务状态（仅在WebSocket未连接时使用）
        async loadRunningTasksStatus() {
            try {
                const data = await this.apiRequest('/api/tasks/running/status');
                // 更新运行中的任务集合
                this.runningTasks.clear();
                data.running_tasks.forEach(taskId => {
                    this.runningTasks.add(taskId);
                });
            } catch (error) {
                // 静默处理错误，避免频繁的错误提示
                console.error('获取运行状态失败:', error);
            }
        },

        // 版本升级相关方法
        async checkVersionUpdate() {
            try {
                const response = await fetch('/api/settings/check-version');
                if (response.ok) {
                    this.versionInfo = await response.json();
                    // console.log('版本检查结果:', this.versionInfo);
                }
            } catch (error) {
                console.error('检查版本更新失败:', error);
            }
        },

        showVersionUpgradeModal() {
            this.showVersionModal = true;
        },

        closeVersionModal() {
            this.showVersionModal = false;
        },

        // 判断当前版本是否大于最新版本
        isCurrentVersionNewer() {
            if (!this.versionInfo.current_version || !this.versionInfo.latest_version) {
                return false;
            }

            try {
                // 移除版本号前的'v'字符
                const current = this.versionInfo.current_version.replace(/^v/, '');
                const latest = this.versionInfo.latest_version.replace(/^v/, '');

                // 分割版本号
                const currentParts = current.split('.').map(x => parseInt(x) || 0);
                const latestParts = latest.split('.').map(x => parseInt(x) || 0);

                // 补齐版本号长度
                const maxLen = Math.max(currentParts.length, latestParts.length);
                while (currentParts.length < maxLen) currentParts.push(0);
                while (latestParts.length < maxLen) latestParts.push(0);

                // 比较版本号
                for (let i = 0; i < maxLen; i++) {
                    if (currentParts[i] > latestParts[i]) {
                        return true;
                    } else if (currentParts[i] < latestParts[i]) {
                        return false;
                    }
                }

                return false; // 版本相等
            } catch (error) {
                console.error('版本比较失败:', error);
                return false;
            }
        },

        copyDownloadUrl() {
            if (this.versionInfo.download_url) {
                navigator.clipboard.writeText(this.versionInfo.download_url).then(() => {
                    this.showToast('下载链接已复制到剪贴板', 'success');
                }).catch(() => {
                    // 降级方案：创建临时文本框
                    const textArea = document.createElement('textarea');
                    textArea.value = this.versionInfo.download_url;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    this.showToast('下载链接已复制到剪贴板', 'success');
                });
            }
        },

        // 接口调试相关方法
        async loadDebugConfigs() {
            try {
                this.debugConfigs = await this.apiRequest('/api/debug/configs');
            } catch (error) {
                console.error('加载接口调试配置失败:', error);
                this.debugConfigs = [];
            }
        },

        // 获取正确的User-Agent值
        getUserAgent() {
            const version = this.versionInfo.current_version || '1.0.0';
            return `Pinchy/${version}`;
        },

        // 更新User-Agent头的值
        updateUserAgent() {
            const userAgentHeader = this.quickDebugForm.headers.find(h => h.key === 'User-Agent');
            if (userAgentHeader) {
                userAgentHeader.value = this.getUserAgent();
            }
        },

        async loadAvailableVariables() {
            try {
                this.availableVariables = await this.apiRequest('/api/debug/variables');
            } catch (error) {
                console.error('加载可用变量失败:', error);
                this.availableVariables = [];
            }
        },

        resetDebugConfigForm() {
            this.debugConfigForm = {
                name: '',
                description: '',
                method: 'GET',
                url: '',
                headers: {},
                headersText: '',
                payload: '',
                notification_type: '',
                notification_enabled: false,
                notification_condition: 'always',
                cron_expression: '',
                is_active: false
            };
        },

        resetQuickDebugForm() {
            this.quickDebugForm = {
                method: 'GET',
                url: '',
                headers: [
                    { key: 'Host', value: '', readonly: true },
                    { key: 'Content-Length', value: '自动计算', readonly: true },
                    { key: 'User-Agent', value: this.getUserAgent(), readonly: false }
                ],
                payload: '',
                notification_type: '',
                notification_enabled: false,
                notification_condition: 'always'
            };
            this.quickDebugResult = null;
        },

        updateQuickDebugHeaders() {
            // 更新Host头
            const hostHeader = this.quickDebugForm.headers.find(h => h.key === 'Host');
            if (hostHeader && this.quickDebugForm.url) {
                try {
                    const url = new URL(this.quickDebugForm.url);
                    hostHeader.value = url.host;
                } catch (e) {
                    hostHeader.value = '';
                }
            }

            // 更新Content-Length头
            const contentLengthHeader = this.quickDebugForm.headers.find(h => h.key === 'Content-Length');
            if (contentLengthHeader) {
                if (this.quickDebugForm.payload && ['POST', 'PUT', 'PATCH'].includes(this.quickDebugForm.method)) {
                    // 检查payload是否包含变量，如果包含变量则设置为自动计算
                    if (this.hasVariables(this.quickDebugForm.payload)) {
                        contentLengthHeader.value = '自动计算';
                    } else {
                        contentLengthHeader.value = new Blob([this.quickDebugForm.payload]).size.toString();
                    }
                } else {
                    contentLengthHeader.value = '自动计算';
                }
            }
        },

        // 检查文本是否包含变量
        hasVariables(text) {
            if (!text) return false;

            // 检查是否包含任何类型的变量
            const variablePatterns = [
                /\[timestmp\.?\d*\]/g,      // 时间戳变量
                /\[getenv\.[^\]]+\]/g,     // 环境变量
                /\[random\.[^\]]+\]/g      // 随机数变量
            ];

            return variablePatterns.some(pattern => pattern.test(text));
        },

        // 验证变量是否正确配置
        validateVariables(text) {
            if (!text) return { valid: true };

            // 检查是否有未指定的环境变量
            const invalidEnvVars = text.match(/\[getenv\.XXX\]/g);
            if (invalidEnvVars) {
                return {
                    valid: false,
                    message: '请将 [getenv.XXX] 中的 XXX 替换为具体的环境变量名'
                };
            }

            return { valid: true };
        },

        async executeQuickDebug() {
            if (!this.quickDebugForm.url) {
                this.showToast('请输入请求URL', 'error');
                return;
            }

            // 验证URL中的变量
            const urlValidation = this.validateVariables(this.quickDebugForm.url);
            if (!urlValidation.valid) {
                this.showToast('URL中的变量配置错误: ' + urlValidation.message, 'error');
                return;
            }

            // 验证请求头中的变量
            for (const header of this.quickDebugForm.headers) {
                const keyValidation = this.validateVariables(header.key);
                const valueValidation = this.validateVariables(header.value);

                if (!keyValidation.valid) {
                    this.showToast(`请求头名称中的变量配置错误: ${keyValidation.message}`, 'error');
                    return;
                }

                if (!valueValidation.valid) {
                    this.showToast(`请求头值中的变量配置错误: ${valueValidation.message}`, 'error');
                    return;
                }
            }

            // 验证请求体中的变量
            if (this.quickDebugForm.payload) {
                const payloadValidation = this.validateVariables(this.quickDebugForm.payload);
                if (!payloadValidation.valid) {
                    this.showToast('请求体中的变量配置错误: ' + payloadValidation.message, 'error');
                    return;
                }
            }

            this.quickDebugExecuting = true;
            try {
                // 转换headers数组为对象
                const headers = {};
                this.quickDebugForm.headers.forEach(header => {
                    if (header.key && header.value) {
                        headers[header.key] = header.value;
                    }
                });

                const requestData = {
                    method: this.quickDebugForm.method,
                    url: this.quickDebugForm.url,
                    headers: headers,
                    payload: this.quickDebugForm.payload,
                    notification_type: this.quickDebugForm.notification_type,
                    notification_enabled: this.quickDebugForm.notification_enabled,
                    notification_condition: this.quickDebugForm.notification_condition
                };

                this.quickDebugResult = await this.apiRequest('/api/debug/execute', {
                    method: 'POST',
                    body: JSON.stringify(requestData)
                });

                this.responseTab = 'body'; // 默认显示响应体
                this.showToast('请求执行完成', 'success');
            } catch (error) {
                console.error('执行请求失败:', error);
                this.showToast('请求执行失败: ' + error.message, 'error');
            } finally {
                this.quickDebugExecuting = false;
            }
        },

        async executeDebugConfig(config) {
            try {
                const requestData = {
                    method: config.method,
                    url: config.url,
                    headers: config.headers || {},
                    payload: config.payload,
                    notification_type: config.notification_type,
                    notification_enabled: config.notification_enabled,
                    notification_condition: config.notification_condition
                };

                const result = await this.apiRequest('/api/debug/execute', {
                    method: 'POST',
                    body: JSON.stringify(requestData)
                });

                this.quickDebugResult = result;
                this.responseTab = 'body';
                this.showToast(`配置 "${config.name}" 执行完成`, 'success');
            } catch (error) {
                console.error('执行配置失败:', error);
                this.showToast('执行配置失败: ' + error.message, 'error');
            }
        },

        editDebugConfig(config) {
            this.editingDebugConfig = config;
            this.debugConfigForm = {
                name: config.name,
                description: config.description || '',
                method: config.method,
                url: config.url,
                headers: config.headers || {},
                headersText: JSON.stringify(config.headers || {}, null, 2),
                payload: config.payload || '',
                notification_type: config.notification_type || '',
                notification_enabled: config.notification_enabled || false,
                notification_condition: config.notification_condition || 'always',
                cron_expression: config.cron_expression || '',
                is_active: config.is_active || false
            };
            this.showDebugConfigModal = true;
        },

        async saveDebugConfig() {
            try {
                // 处理headers JSON转换
                let headers = {};
                if (this.debugConfigForm.headersText.trim()) {
                    try {
                        headers = JSON.parse(this.debugConfigForm.headersText);
                    } catch (e) {
                        this.showToast('请求头JSON格式错误', 'error');
                        return;
                    }
                }

                const configData = {
                    ...this.debugConfigForm,
                    headers: headers
                };
                delete configData.headersText; // 移除临时字段

                if (this.editingDebugConfig) {
                    await this.apiRequest(`/api/debug/configs/${this.editingDebugConfig.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(configData)
                    });
                    this.showToast('配置更新成功', 'success');
                } else {
                    await this.apiRequest('/api/debug/configs', {
                        method: 'POST',
                        body: JSON.stringify(configData)
                    });
                    this.showToast('配置创建成功', 'success');
                }
                this.showDebugConfigModal = false;
                this.editingDebugConfig = null;
                this.resetDebugConfigForm();
                await this.loadDebugConfigs();
            } catch (error) {
                console.error('保存配置失败:', error);
                this.showToast('保存配置失败: ' + error.message, 'error');
            }
        },

        async deleteDebugConfig(configId) {
            if (!confirm('确定要删除这个配置吗？')) return;

            try {
                await this.apiRequest(`/api/debug/configs/${configId}`, {
                    method: 'DELETE'
                });
                this.showToast('配置删除成功', 'success');
                await this.loadDebugConfigs();
            } catch (error) {
                console.error('删除配置失败:', error);
                this.showToast('删除配置失败: ' + error.message, 'error');
            }
        },

        async importRequest() {
            if (!this.importContent.trim()) {
                this.showToast('请输入cURL或fetch命令', 'error');
                return;
            }

            try {
                const result = await this.apiRequest('/api/debug/import', {
                    method: 'POST',
                    body: JSON.stringify({ content: this.importContent })
                });

                // 将导入的结果填充到快速调试表单
                this.quickDebugForm.method = result.method || 'GET';
                this.quickDebugForm.url = result.url || '';
                this.quickDebugForm.payload = result.payload || '';

                // 重置headers，保留默认的Host、Content-Length和User-Agent
                this.quickDebugForm.headers = [
                    { key: 'Host', value: '', readonly: true },
                    { key: 'Content-Length', value: '自动计算', readonly: true },
                    { key: 'User-Agent', value: this.getUserAgent(), readonly: false }
                ];

                // 添加导入的headers
                Object.entries(result.headers || {}).forEach(([key, value]) => {
                    const lowerKey = key.toLowerCase();

                    if (lowerKey === 'host') {
                        // 更新Host头的值
                        const hostHeader = this.quickDebugForm.headers.find(h => h.key === 'Host');
                        if (hostHeader) {
                            hostHeader.value = value;
                        }
                    } else if (lowerKey === 'user-agent') {
                        // 更新User-Agent头的值
                        const userAgentHeader = this.quickDebugForm.headers.find(h => h.key === 'User-Agent');
                        if (userAgentHeader) {
                            userAgentHeader.value = value;
                        }
                    } else if (lowerKey !== 'content-length') {
                        // 添加其他headers（跳过Content-Length）
                        this.quickDebugForm.headers.push({ key, value, readonly: false });
                    }
                });

                // 更新默认headers（这会自动设置Host如果URL有效）
                this.updateQuickDebugHeaders();

                this.showImportModal = false;
                this.importContent = '';
                this.showToast('导入成功', 'success');
            } catch (error) {
                console.error('导入失败:', error);
                this.showToast('导入失败: ' + error.message, 'error');
            }
        },

        getMethodColor(method) {
            const colors = {
                'GET': 'bg-green-100 text-green-800',
                'POST': 'bg-blue-100 text-blue-800',
                'PUT': 'bg-yellow-100 text-yellow-800',
                'DELETE': 'bg-red-100 text-red-800',
                'PATCH': 'bg-purple-100 text-purple-800',
                'HEAD': 'bg-gray-100 text-gray-800',
                'OPTIONS': 'bg-indigo-100 text-indigo-800'
            };
            return colors[method] || 'bg-gray-100 text-gray-800';
        },

        copyVariableName(variableName) {
            navigator.clipboard.writeText(variableName).then(() => {
                this.showToast('变量名已复制', 'success');
            }).catch(() => {
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = variableName;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                this.showToast('变量名已复制', 'success');
            });
        },

        // 将快速调试配置保存为配置
        saveQuickDebugAsConfig() {
            // 验证必填字段
            if (!this.quickDebugForm.url) {
                this.showToast('请先输入请求URL', 'error');
                return;
            }

            // 转换headers数组为JSON对象
            const headers = {};
            this.quickDebugForm.headers.forEach(header => {
                if (header.key && header.value) {
                    // 跳过值为"自动计算"的Content-Length头
                    if (header.key.toLowerCase() === 'content-length' && header.value === '自动计算') {
                        return;
                    }
                    headers[header.key] = header.value;
                }
            });

            // 生成默认配置名称
            const defaultName = `${this.quickDebugForm.method} ${this.quickDebugForm.url}`;
            const truncatedName = defaultName.length > 50 ? defaultName.substring(0, 47) + '...' : defaultName;

            // 回填到配置表单
            this.debugConfigForm = {
                name: truncatedName,
                description: `从快速调试保存的配置 - ${new Date().toLocaleString()}`,
                method: this.quickDebugForm.method,
                url: this.quickDebugForm.url,
                headers: headers,
                headersText: JSON.stringify(headers, null, 2),
                payload: this.quickDebugForm.payload || '',
                notification_type: this.quickDebugForm.notification_type || '',
                notification_enabled: this.quickDebugForm.notification_enabled || false,
                notification_condition: this.quickDebugForm.notification_condition || 'always',
                cron_expression: '',
                is_active: false
            };

            // 清空编辑状态并打开模态框
            this.editingDebugConfig = null;
            this.showDebugConfigModal = true;

            this.showToast('配置已回填到新建配置表单', 'success');
        },

        // 脚本订阅相关方法
        async loadSubscriptions() {
            this.subscriptionsLoading = true;
            try {
                const response = await fetch('/api/subscriptions/');
                if (response.ok) {
                    this.subscriptions = await response.json();
                } else {
                    this.showToast('加载订阅列表失败', 'error');
                }
            } catch (error) {
                console.error('加载订阅列表失败:', error);
                this.showToast('加载订阅列表失败', 'error');
            } finally {
                this.subscriptionsLoading = false;
            }
        },

        async loadProxyConfig() {
            try {
                const response = await fetch('/api/subscriptions/proxy');
                if (response.ok) {
                    this.proxyConfig = await response.json();
                }
            } catch (error) {
                console.error('加载代理配置失败:', error);
            }
        },

        async saveProxyConfig() {
            try {
                const response = await fetch('/api/subscriptions/proxy', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(this.proxyConfig)
                });

                if (response.ok) {
                    this.showToast('代理配置已保存', 'success');
                    this.showProxyConfigModal = false;
                } else {
                    this.showToast('保存代理配置失败', 'error');
                }
            } catch (error) {
                console.error('保存代理配置失败:', error);
                this.showToast('保存代理配置失败', 'error');
            }
        },

        openSubscriptionModal(subscription = null) {
            this.editingSubscription = subscription;
            if (subscription) {
                this.subscriptionForm = {
                    name: subscription.name,
                    description: subscription.description || '',
                    git_url: subscription.git_url,
                    save_directory: subscription.save_directory,
                    file_extensions: Array.isArray(subscription.file_extensions) ? subscription.file_extensions.join(', ') : '',
                    exclude_patterns: Array.isArray(subscription.exclude_patterns) ? subscription.exclude_patterns.join(', ') : '',
                    include_folders: subscription.include_folders,
                    include_subfolders: subscription.include_subfolders,
                    use_proxy: subscription.use_proxy,
                    sync_delete_removed_files: subscription.sync_delete_removed_files || false,
                    cron_expression: subscription.cron_expression,
                    notification_enabled: subscription.notification_enabled,
                    notification_type: subscription.notification_type || ''
                };
            } else {
                this.subscriptionForm = {
                    name: '',
                    description: '',
                    git_url: '',
                    save_directory: '',
                    file_extensions: '',
                    exclude_patterns: '.git, .github, .gitignore, .gitattributes, LICENSE, node_modules, __pycache__, .DS_Store, Thumbs.db',
                    include_folders: true,
                    include_subfolders: true,
                    use_proxy: false,
                    sync_delete_removed_files: false,
                    cron_expression: '0 0 * * *',
                    notification_enabled: false,
                    notification_type: ''
                };
            }
            this.showSubscriptionModal = true;
        },

        async saveSubscription() {
            try {
                // 验证必填字段
                if (!this.subscriptionForm.name || !this.subscriptionForm.git_url || !this.subscriptionForm.cron_expression) {
                    this.showToast('请填写必填字段', 'error');
                    return;
                }

                // 如果没有指定保存目录，根据Git URL自动生成
                if (!this.subscriptionForm.save_directory) {
                    const urlParts = this.subscriptionForm.git_url.split('/');
                    if (urlParts.length >= 2) {
                        const username = urlParts[urlParts.length - 2];
                        const repoName = urlParts[urlParts.length - 1].replace('.git', '');
                        this.subscriptionForm.save_directory = `${username}_${repoName}`;
                    } else {
                        const repoName = this.subscriptionForm.git_url.split('/').pop().replace('.git', '');
                        this.subscriptionForm.save_directory = repoName;
                    }
                }

                // 处理文件扩展名
                let fileExtensions = [];
                if (this.subscriptionForm.file_extensions) {
                    if (typeof this.subscriptionForm.file_extensions === 'string') {
                        fileExtensions = this.subscriptionForm.file_extensions.split(',').map(ext => ext.trim()).filter(ext => ext);
                    } else {
                        fileExtensions = this.subscriptionForm.file_extensions;
                    }
                }

                // 处理排除模式
                let excludePatterns = [];
                if (this.subscriptionForm.exclude_patterns) {
                    if (typeof this.subscriptionForm.exclude_patterns === 'string') {
                        excludePatterns = this.subscriptionForm.exclude_patterns.split(',').map(pattern => pattern.trim()).filter(pattern => pattern);
                    } else {
                        excludePatterns = this.subscriptionForm.exclude_patterns;
                    }
                }

                const formData = {
                    ...this.subscriptionForm,
                    file_extensions: fileExtensions,
                    exclude_patterns: excludePatterns
                };

                const url = this.editingSubscription
                    ? `/api/subscriptions/${this.editingSubscription.id}`
                    : '/api/subscriptions/';

                const method = this.editingSubscription ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                if (response.ok) {
                    const savedSubscription = await response.json();
                    this.showToast(this.editingSubscription ? '订阅已更新' : '订阅已创建', 'success');
                    this.showSubscriptionModal = false;
                    await this.loadSubscriptions();

                    // 如果是新建订阅，自动执行一次同步
                    if (!this.editingSubscription) {
                        await this.syncSubscription(savedSubscription);
                    }
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '保存订阅失败', 'error');
                }
            } catch (error) {
                console.error('保存订阅失败:', error);
                this.showToast('保存订阅失败', 'error');
            }
        },

        async deleteSubscription(subscription) {
            if (!confirm(`确定要删除订阅 "${subscription.name}" 吗？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/subscriptions/${subscription.id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    this.showToast('订阅已删除', 'success');
                    await this.loadSubscriptions();
                } else {
                    this.showToast('删除订阅失败', 'error');
                }
            } catch (error) {
                console.error('删除订阅失败:', error);
                this.showToast('删除订阅失败', 'error');
            }
        },

        async syncSubscription(subscription) {
            try {
                // 添加到同步中的集合
                this.syncingSubscriptions.add(subscription.id);

                const response = await fetch(`/api/subscriptions/${subscription.id}/sync`, {
                    method: 'POST'
                });

                if (response.ok) {
                    this.showToast(`订阅 "${subscription.name}" 同步已开始`, 'success');
                    // WebSocket会处理同步完成的消息
                } else {
                    this.syncingSubscriptions.delete(subscription.id);
                    this.showToast('同步订阅失败', 'error');
                }
            } catch (error) {
                this.syncingSubscriptions.delete(subscription.id);
                console.error('同步订阅失败:', error);
                this.showToast('同步订阅失败', 'error');
            }
        },

        async loadSubscriptionLogs(subscription) {
            this.currentSubscriptionLogs = subscription;
            this.subscriptionLogsLoading = true;
            try {
                const response = await fetch(`/api/subscriptions/${subscription.id}/logs`);
                if (response.ok) {
                    this.subscriptionLogs = await response.json();
                    this.showSubscriptionLogsModal = true;
                } else {
                    this.showToast('加载订阅日志失败', 'error');
                }
            } catch (error) {
                console.error('加载订阅日志失败:', error);
                this.showToast('加载订阅日志失败', 'error');
            } finally {
                this.subscriptionLogsLoading = false;
            }
        },

        formatFileExtensions(extensions) {
            if (!extensions || extensions.length === 0) {
                return '所有文件';
            }
            return extensions.join(', ');
        },

        formatLastSyncTime(time) {
            if (!time) {
                return '从未同步';
            }
            return new Date(time).toLocaleString();
        },

        isSyncingSubscription(subscriptionId) {
            return this.syncingSubscriptions.has(subscriptionId);
        },

        // requirements.txt依赖检查相关方法
        async checkRequirements(subscription) {
            this.currentRequirementsSubscription = subscription;
            this.requirementsLoading = true;
            this.requirementsData = null;
            this.showRequirementsModal = true;

            try {
                const response = await fetch(`/api/subscriptions/${subscription.id}/requirements`);
                if (response.ok) {
                    this.requirementsData = await response.json();
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || '检查依赖失败', 'error');
                    this.showRequirementsModal = false;
                }
            } catch (error) {
                console.error('检查依赖失败:', error);
                this.showToast('检查依赖失败', 'error');
                this.showRequirementsModal = false;
            } finally {
                this.requirementsLoading = false;
            }
        },

        // 检查订阅是否包含requirements.txt
        async hasRequirements(subscription) {
            try {
                // 通过API检查订阅目录中是否存在requirements.txt文件
                const response = await fetch(`/api/subscriptions/${subscription.id}/requirements`);
                return response.status === 200;
            } catch (error) {
                console.error('检查requirements.txt失败:', error);
                return false;
            }
        },

        // 获取版本比较状态的显示文本和样式
        getVersionStatus(required, installed, operator) {
            if (!installed) {
                return { text: '未安装', class: 'text-red-600 bg-red-50' };
            }

            if (!required || !operator) {
                return { text: '已安装', class: 'text-green-600 bg-green-50' };
            }

            // 解析版本号为数字数组进行比较
            const parseVersion = (version) => {
                return version.replace(/[^\d.]/g, '').split('.').map(num => parseInt(num) || 0);
            };

            const reqParts = parseVersion(required);
            const instParts = parseVersion(installed);

            // 补齐版本号长度
            const maxLength = Math.max(reqParts.length, instParts.length);
            while (reqParts.length < maxLength) reqParts.push(0);
            while (instParts.length < maxLength) instParts.push(0);

            // 比较版本号
            const compareVersions = (v1, v2) => {
                for (let i = 0; i < v1.length; i++) {
                    if (v1[i] > v2[i]) return 1;
                    if (v1[i] < v2[i]) return -1;
                }
                return 0;
            };

            const comparison = compareVersions(instParts, reqParts);

            switch (operator) {
                case '==':
                    if (comparison === 0) {
                        return { text: '版本相同', class: 'text-green-600 bg-green-50' };
                    } else if (comparison > 0) {
                        return { text: '需要降级', class: 'text-orange-600 bg-orange-50' };
                    } else {
                        return { text: '需要升级', class: 'text-blue-600 bg-blue-50' };
                    }
                case '>=':
                    if (comparison >= 0) {
                        return { text: '已安装', class: 'text-green-600 bg-green-50' };
                    } else {
                        return { text: '需要升级', class: 'text-blue-600 bg-blue-50' };
                    }
                case '>':
                    if (comparison > 0) {
                        return { text: '已安装', class: 'text-green-600 bg-green-50' };
                    } else {
                        return { text: '需要升级', class: 'text-blue-600 bg-blue-50' };
                    }
                case '<=':
                    if (comparison <= 0) {
                        return { text: '已安装', class: 'text-green-600 bg-green-50' };
                    } else {
                        return { text: '需要降级', class: 'text-orange-600 bg-orange-50' };
                    }
                case '<':
                    if (comparison < 0) {
                        return { text: '已安装', class: 'text-green-600 bg-green-50' };
                    } else {
                        return { text: '需要降级', class: 'text-orange-600 bg-orange-50' };
                    }
                default:
                    return { text: '已安装', class: 'text-green-600 bg-green-50' };
            }
        },

        // 检查代理是否可用（用于禁用使用代理选项）
        isProxyAvailable() {
            return this.proxyConfig.enabled && this.proxyConfig.host && this.proxyConfig.port;
        },

        // 安全配置相关方法
        async loadSecurityConfig() {
            this.securityConfigLoading = true;
            try {
                this.securityConfig = await this.apiRequest('/api/settings/security-config');
            } catch (error) {
                console.error('加载安全配置失败:', error);
                this.securityConfig = {
                    captcha_enabled: false,
                    ip_blocking_enabled: false,
                    mfa_enabled: false,
                    mfa_notification_type: '',
                    available_notifications: []
                };
            } finally {
                this.securityConfigLoading = false;
            }
        },

        async saveSecurityConfig() {
            this.securityConfigSaving = true;
            try {
                await this.apiRequest('/api/settings/security-config', {
                    method: 'POST',
                    body: JSON.stringify({
                        captcha_enabled: this.securityConfig.captcha_enabled,
                        ip_blocking_enabled: this.securityConfig.ip_blocking_enabled,
                        mfa_enabled: this.securityConfig.mfa_enabled,
                        mfa_notification_type: this.securityConfig.mfa_notification_type
                    })
                });
                this.showToast('安全配置保存成功', 'success');
                // 重新加载安全状态
                await this.loadSecurityStatus();
            } catch (error) {
                console.error('保存安全配置失败:', error);
            } finally {
                this.securityConfigSaving = false;
            }
        },

        // 时区配置相关方法
        async loadTimezoneConfig() {
            this.timezoneConfigLoading = true;
            try {
                this.timezoneConfig = await this.apiRequest('/api/settings/timezone-config');
                // 设置当前选中的时区
                if (this.timezoneConfig && this.timezoneConfig.current_timezone) {
                    this.selectedTimezone = this.timezoneConfig.current_timezone;
                }
            } catch (error) {
                console.error('加载时区配置失败:', error);
                this.showToast('加载时区配置失败', 'error');
            } finally {
                this.timezoneConfigLoading = false;
            }
        },

        async refreshTimezoneConfig() {
            await this.loadTimezoneConfig();
            // 同时刷新系统信息以获取最新时间
            await this.loadSystemInfo();
            this.showToast('时区配置已刷新', 'success');
        },

        async updateTimezone() {
            if (!this.selectedTimezone) {
                this.showToast('请选择时区', 'warning');
                return;
            }

            this.timezoneUpdating = true;
            try {
                await this.apiRequest('/api/settings/timezone-config', {
                    method: 'POST',
                    body: JSON.stringify({
                        timezone: this.selectedTimezone
                    })
                });

                this.showToast('时区设置已更新', 'success');

                // 重新加载时区配置和系统信息
                await this.loadTimezoneConfig();
                await this.loadSystemInfo();

            } catch (error) {
                console.error('更新时区设置失败:', error);
                this.showToast('更新时区设置失败: ' + (error.message || '未知错误'), 'error');
            } finally {
                this.timezoneUpdating = false;
            }
        }
    };
}
