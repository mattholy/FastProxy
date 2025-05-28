// commitlint.config.js
const { defineConfig } = require('cz-git');

module.exports = {
    // —— cz-git 提问配置 —— 
    ...defineConfig({
        prompt: {
            types: [
                { value: 'feat', name: 'feat:     新增功能' },
                { value: 'fix', name: 'fix:      修复缺陷' },
                { value: 'docs', name: 'docs:     文档更新' },
                { value: 'style', name: 'style:    代码格式（不影响功能）' },
                { value: 'refactor', name: 'refactor: 重构（既不是新增功能，也不是修复bug）' },
                { value: 'perf', name: 'perf:     性能优化' },
                { value: 'test', name: 'test:     添加/修改测试' },
                { value: 'build', name: 'build:    构建相关修改' },
                { value: 'ci', name: 'ci:       CI 配置相关修改' },
                { value: 'chore', name: 'chore:    构建过程或辅助工具变动' },
                { value: 'revert', name: 'revert:   回退到上一个版本' }
            ],
            // —— scope 列表改为 Python 库常见模块 —— 
            scopes: [
                { value: 'core', name: 'core:    核心功能模块' },
                { value: 'cli', name: 'cli:     命令行工具' },
                { value: 'docs', name: 'docs:    文档' },
                { value: 'tests', name: 'tests:   测试' },
                { value: 'setup', name: 'setup:   安装/打包脚本' },
                { value: 'ci', name: 'ci:      CI 配置' }
            ],
            messages: {
                type: '请选择提交类型：',
                scope: '请输入修改范围（可多选，用空格/方向键选中，回车确认）：',
                customScope: '请输入自定义修改范围：',
                subject: '请简要描述提交（必填）：',
                body: '请输入详细描述（可选）：',
                breaking: '列出非兼容性重大变更（可选）：',
                footerPrefixesSelect: '请选择 Issue 操作（关联 / 关闭 / 跳过）：',
                customFooterPrefix: '请输入自定义 Issue 前缀：',
                footer: '列出要关联或关闭的 Issue 编号（示例：#123, #456，可选）：',
                confirmCommit: '确认要提交吗？'
            },
            allowCustomScopes: false,
            allowEmptyScopes: false,
            allowBreakingChanges: ['feat', 'fix'],
            enableMultipleScopes: true,
            scopeEnumSeparator: ',',
            issuePrefixes: [
                { value: 'Associate', name: '关联Issues' },
                { value: 'Close', name: '关闭Issues' }
            ],
            emptyIssuePrefixAlias: '跳过',
            allowCustomIssuePrefix: false,
            allowEmptyIssuePrefix: true,
        }
    }),

    // —— CommitLint 校验规则 —— 
    extends: ['@commitlint/config-conventional'],
    rules: {
        'type-enum': [2, 'always', [
            'feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert'
        ]],
        // —— scope-enum 同步更新 —— 
        'scope-enum': [2, 'always', ['core', 'cli', 'docs', 'tests', 'setup', 'ci']],
        'scope-empty': [2, 'never'],
        'subject-empty': [2, 'never'],
        'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
        'header-max-length': [2, 'always', 72]
    }
};
