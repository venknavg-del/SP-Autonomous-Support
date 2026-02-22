/**
 * LLM Proxy Server — Exposes GitHub Copilot's LLM as a local HTTP endpoint.
 * 
 * Python backend agents POST to http://127.0.0.1:9100/v1/chat with:
 *   { messages: [{role, content}], model_family?: string }
 * 
 * The proxy forwards the request to Copilot via vscode.lm API and returns
 * the response as { content: string }.
 */

import * as vscode from 'vscode';
import * as http from 'http';

const PORT = 9100;

interface ChatMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

interface ChatRequest {
    messages: ChatMessage[];
    model_family?: string;
}

function readBody(req: http.IncomingMessage): Promise<string> {
    return new Promise((resolve, reject) => {
        const chunks: Buffer[] = [];
        req.on('data', (chunk: Buffer) => chunks.push(chunk));
        req.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
        req.on('error', reject);
    });
}

export class LLMProxyServer {
    private server: http.Server | null = null;
    private outputChannel: vscode.OutputChannel;

    constructor(outputChannel: vscode.OutputChannel) {
        this.outputChannel = outputChannel;
    }

    start(): Promise<void> {
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
                        const chatReq: ChatRequest = JSON.parse(body);

                        this.outputChannel.appendLine(
                            `[LLM Proxy] Request: ${chatReq.messages.length} messages, family: ${chatReq.model_family || 'gpt-4o'}`
                        );

                        const result = await this.callCopilot(chatReq);

                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ content: result }));

                        this.outputChannel.appendLine(
                            `[LLM Proxy] Response: ${result.length} chars`
                        );
                    } catch (err: any) {
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

            this.server.on('error', (err: any) => {
                if (err.code === 'EADDRINUSE') {
                    this.outputChannel.appendLine(`[LLM Proxy] Port ${PORT} already in use — another instance may be running`);
                    resolve(); // Don't reject — could be another instance
                } else {
                    reject(err);
                }
            });
        });
    }

    private async callCopilot(chatReq: ChatRequest): Promise<string> {
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
                (error as any).code = 'NoModels';
                throw error;
            }
            // Use first available model
            this.outputChannel.appendLine(`[LLM Proxy] Requested ${family} not found, using ${allModels[0].id}`);
            return this.sendToModel(allModels[0], chatReq.messages);
        }

        return this.sendToModel(models[0], chatReq.messages);
    }

    private async sendToModel(
        model: vscode.LanguageModelChat,
        messages: ChatMessage[]
    ): Promise<string> {
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
        } finally {
            clearTimeout(timeout);
            tokenSource.dispose();
        }
    }

    stop(): void {
        if (this.server) {
            this.server.close();
            this.server = null;
            this.outputChannel.appendLine('[LLM Proxy] Server stopped');
        }
    }

    get isRunning(): boolean {
        return this.server !== null && this.server.listening;
    }
}
