import * as vscode from 'vscode';
import { LLMProxyServer } from './llmProxy';

let proxyServer: LLMProxyServer | undefined;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    const outputChannel = vscode.window.createOutputChannel('SP Support LLM Proxy');
    outputChannel.appendLine('[Extension] SP Autonomous Support extension activated');

    proxyServer = new LLMProxyServer(outputChannel);

    // Status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'spSupport.status';
    context.subscriptions.push(statusBarItem);
    updateStatusBar();

    // Commands
    context.subscriptions.push(
        vscode.commands.registerCommand('spSupport.startProxy', async () => {
            if (proxyServer?.isRunning) {
                vscode.window.showInformationMessage('SP Support LLM Proxy is already running on port 9100');
                return;
            }

            try {
                await proxyServer?.start();
                updateStatusBar();
                vscode.window.showInformationMessage('SP Support LLM Proxy started on port 9100');
            } catch (err: any) {
                vscode.window.showErrorMessage(`Failed to start proxy: ${err.message}`);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('spSupport.stopProxy', () => {
            if (!proxyServer?.isRunning) {
                vscode.window.showInformationMessage('SP Support LLM Proxy is not running');
                return;
            }

            proxyServer.stop();
            updateStatusBar();
            vscode.window.showInformationMessage('SP Support LLM Proxy stopped');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('spSupport.status', () => {
            const status = proxyServer?.isRunning ? 'Running on port 9100' : 'Stopped';
            vscode.window.showInformationMessage(`SP Support LLM Proxy Status: ${status}`);
            outputChannel.show();
        })
    );

    // Auto-start the proxy on activation
    vscode.commands.executeCommand('spSupport.startProxy');
}

function updateStatusBar() {
    if (proxyServer?.isRunning) {
        statusBarItem.text = '$(zap) SP Proxy: ON';
        statusBarItem.tooltip = 'SP Support LLM Proxy running on port 9100. Click for status.';
        statusBarItem.backgroundColor = undefined;
        statusBarItem.show();
    } else {
        statusBarItem.text = '$(circle-slash) SP Proxy: OFF';
        statusBarItem.tooltip = 'SP Support LLM Proxy is stopped. Click to see details.';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        statusBarItem.show();
    }
}

export function deactivate() {
    if (proxyServer) {
        proxyServer.stop();
    }
}
