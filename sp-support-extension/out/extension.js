"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const llmProxy_1 = require("./llmProxy");
let proxyServer;
let statusBarItem;
function activate(context) {
    const outputChannel = vscode.window.createOutputChannel('SP Support LLM Proxy');
    outputChannel.appendLine('[Extension] SP Autonomous Support extension activated');
    proxyServer = new llmProxy_1.LLMProxyServer(outputChannel);
    // Status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'spSupport.status';
    context.subscriptions.push(statusBarItem);
    updateStatusBar();
    // Commands
    context.subscriptions.push(vscode.commands.registerCommand('spSupport.startProxy', async () => {
        if (proxyServer?.isRunning) {
            vscode.window.showInformationMessage('SP Support LLM Proxy is already running on port 9100');
            return;
        }
        try {
            await proxyServer?.start();
            updateStatusBar();
            vscode.window.showInformationMessage('SP Support LLM Proxy started on port 9100');
        }
        catch (err) {
            vscode.window.showErrorMessage(`Failed to start proxy: ${err.message}`);
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('spSupport.stopProxy', () => {
        if (!proxyServer?.isRunning) {
            vscode.window.showInformationMessage('SP Support LLM Proxy is not running');
            return;
        }
        proxyServer.stop();
        updateStatusBar();
        vscode.window.showInformationMessage('SP Support LLM Proxy stopped');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('spSupport.status', () => {
        const status = proxyServer?.isRunning ? 'Running on port 9100' : 'Stopped';
        vscode.window.showInformationMessage(`SP Support LLM Proxy Status: ${status}`);
        outputChannel.show();
    }));
    // Auto-start the proxy on activation
    vscode.commands.executeCommand('spSupport.startProxy');
}
function updateStatusBar() {
    if (proxyServer?.isRunning) {
        statusBarItem.text = '$(zap) SP Proxy: ON';
        statusBarItem.tooltip = 'SP Support LLM Proxy running on port 9100. Click for status.';
        statusBarItem.backgroundColor = undefined;
        statusBarItem.show();
    }
    else {
        statusBarItem.text = '$(circle-slash) SP Proxy: OFF';
        statusBarItem.tooltip = 'SP Support LLM Proxy is stopped. Click to see details.';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        statusBarItem.show();
    }
}
function deactivate() {
    if (proxyServer) {
        proxyServer.stop();
    }
}
//# sourceMappingURL=extension.js.map