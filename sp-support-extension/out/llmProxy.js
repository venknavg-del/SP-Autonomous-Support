"use strict";
/**
 * LLM Proxy Server — Exposes GitHub Copilot's LLM as a local HTTP endpoint.
 *
 * Python backend agents POST to http://127.0.0.1:9100/v1/chat with:
 *   { messages: [{role, content}], model_family?: string }
 *
 * The proxy forwards the request to Copilot via vscode.lm API and returns
 * the response as { content: string }.
 */
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
exports.LLMProxyServer = void 0;
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
const PORT = 9100;
function readBody(req) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        req.on('data', (chunk) => chunks.push(chunk));
        req.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
        req.on('error', reject);
    });
}
class LLMProxyServer {
    server = null;
    outputChannel;
    constructor(outputChannel) {
        this.outputChannel = outputChannel;
    }
    start() {
        return new Promise((resolve, reject) => {
            this.server = http.createServer(async (req, res) => {
                // CORS headers for local development
                res.setHeader('Access-Control-Allow-Origin', '*');
                res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
                res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
                if (req.method === 'OPTIONS') {
                    res.writeHead(204);
                    res.end();
                    return;
                }
                // Health check
                if (req.method === 'GET' && req.url === '/health') {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: 'ok', provider: 'copilot' }));
                    return;
                }
                // Chat endpoint
                if (req.method === 'POST' && req.url === '/v1/chat') {
                    try {
                        const body = await readBody(req);
                        const chatReq = JSON.parse(body);
                        this.outputChannel.appendLine(`[LLM Proxy] Request: ${chatReq.messages.length} messages, family: ${chatReq.model_family || 'gpt-4o'}`);
                        const result = await this.callCopilot(chatReq);
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ content: result }));
                        this.outputChannel.appendLine(`[LLM Proxy] Response: ${result.length} chars`);
                    }
                    catch (err) {
                        this.outputChannel.appendLine(`[LLM Proxy] Error: ${err.message}`);
                        const statusCode = err.code === 'NoModels' ? 503 : 500;
                        res.writeHead(statusCode, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            error: err.message,
                            code: err.code || 'INTERNAL_ERROR'
                        }));
                    }
                    return;
                }
                // Unknown route
                res.writeHead(404);
                res.end(JSON.stringify({ error: 'Not found' }));
            });
            this.server.listen(PORT, '127.0.0.1', () => {
                this.outputChannel.appendLine(`[LLM Proxy] Listening on http://127.0.0.1:${PORT}`);
                resolve();
            });
            this.server.on('error', (err) => {
                if (err.code === 'EADDRINUSE') {
                    this.outputChannel.appendLine(`[LLM Proxy] Port ${PORT} already in use — another instance may be running`);
                    resolve(); // Don't reject — could be another instance
                }
                else {
                    reject(err);
                }
            });
        });
    }
    async callCopilot(chatReq) {
        // Select a Copilot model
        const family = chatReq.model_family || 'gpt-4o';
        const models = await vscode.lm.selectChatModels({
            vendor: 'copilot',
            family: family
        });
        if (models.length === 0) {
            // Try without family filter
            const allModels = await vscode.lm.selectChatModels({ vendor: 'copilot' });
            if (allModels.length === 0) {
                const error = new Error('No Copilot models available. Ensure GitHub Copilot is active.');
                error.code = 'NoModels';
                throw error;
            }
            // Use first available model
            this.outputChannel.appendLine(`[LLM Proxy] Requested ${family} not found, using ${allModels[0].id}`);
            return this.sendToModel(allModels[0], chatReq.messages);
        }
        return this.sendToModel(models[0], chatReq.messages);
    }
    async sendToModel(model, messages) {
        // Convert messages to VSCode format
        // Note: vscode.lm only has User and Assistant roles (system → User)
        const vsMessages = messages.map(m => {
            if (m.role === 'assistant') {
                return vscode.LanguageModelChatMessage.Assistant(m.content);
            }
            // Both 'system' and 'user' map to User messages
            return vscode.LanguageModelChatMessage.User(m.content);
        });
        const tokenSource = new vscode.CancellationTokenSource();
        // 2 minute timeout
        const timeout = setTimeout(() => tokenSource.cancel(), 120_000);
        try {
            const response = await model.sendRequest(vsMessages, {}, tokenSource.token);
            let fullText = '';
            for await (const chunk of response.text) {
                fullText += chunk;
            }
            return fullText;
        }
        finally {
            clearTimeout(timeout);
            tokenSource.dispose();
        }
    }
    stop() {
        if (this.server) {
            this.server.close();
            this.server = null;
            this.outputChannel.appendLine('[LLM Proxy] Server stopped');
        }
    }
    get isRunning() {
        return this.server !== null && this.server.listening;
    }
}
exports.LLMProxyServer = LLMProxyServer;
//# sourceMappingURL=llmProxy.js.map