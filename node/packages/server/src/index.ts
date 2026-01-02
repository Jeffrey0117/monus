/**
 * Monus Server - Hono HTTP/WebSocket Server
 */

import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { serveStatic } from '@hono/node-server/serve-static';
import { createNodeWebSocket } from '@hono/node-ws';
import { config } from 'dotenv';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

import { Planner, Coder, SandboxTool } from '@monus/core';

// Load environment variables
config();

const __dirname = dirname(fileURLToPath(import.meta.url));

const app = new Hono();

// Middleware
app.use('/*', cors());

// WebSocket setup
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// Initialize tools
const sandbox = new SandboxTool(join(__dirname, '../../..', 'sandbox_workspace'));

// Health check
app.get('/api/health', (c) => {
  return c.json({ status: 'ok', version: '4.0.0' });
});

// List runs (placeholder)
app.get('/api/runs', (c) => {
  return c.json({ runs: [] });
});

// Create task
app.post('/api/tasks', async (c) => {
  const body = await c.req.json();
  const taskId = Date.now().toString();

  return c.json({
    taskId,
    status: 'pending',
    message: 'Task created. Connect to WebSocket to start execution.',
  });
});

// WebSocket endpoint
app.get(
  '/ws/:taskId',
  upgradeWebSocket((c) => {
    const taskId = c.req.param('taskId');

    return {
      onOpen(event, ws) {
        console.log(`[WS] Connected: ${taskId}`);
      },

      async onMessage(event, ws) {
        try {
          const data = JSON.parse(event.data.toString());
          const { goal, output_format, theme, model } = data;

          if (!goal) {
            ws.send(JSON.stringify({ type: 'error', message: 'Goal is required' }));
            return;
          }

          const apiKey = process.env.DEEPSEEK_API_KEY;
          if (!apiKey) {
            ws.send(JSON.stringify({ type: 'error', message: 'DEEPSEEK_API_KEY not configured' }));
            return;
          }

          // Initialize agents
          const planner = new Planner({
            model: model || 'deepseek-chat',
            apiKey,
            baseURL: 'https://api.deepseek.com/v1',
          });

          const coder = new Coder({
            model: model || 'deepseek-chat',
            apiKey,
            baseURL: 'https://api.deepseek.com/v1',
          });

          // Classify task
          const classification = await planner.classifyTask(goal);

          ws.send(
            JSON.stringify({
              type: 'classification',
              taskType: classification.type,
              template: classification.template,
              confidence: classification.confidence,
              reason: classification.reason,
            })
          );

          if (classification.type === 'code') {
            // Code generation mode
            await runCodeGeneration(ws, taskId, goal, classification.template || 'html', coder, sandbox);
          } else {
            // Research mode (simplified)
            await runResearch(ws, taskId, goal, planner);
          }
        } catch (error: any) {
          console.error('[WS] Error:', error);
          ws.send(JSON.stringify({ type: 'error', message: error.message }));
        }
      },

      onClose() {
        console.log(`[WS] Disconnected: ${taskId}`);
      },
    };
  })
);

/**
 * Run code generation
 */
async function runCodeGeneration(
  ws: any,
  taskId: string,
  goal: string,
  template: string,
  coder: Coder,
  sandbox: SandboxTool
) {
  ws.send(JSON.stringify({ type: 'phase', phase: 'planning' }));
  ws.send(JSON.stringify({ type: 'progress', progress: 5 }));

  // Analyze task
  const plan = await coder.analyzeTask(goal, template as any);
  const projectName = plan.projectName;

  ws.send(JSON.stringify({ type: 'progress', progress: 10 }));
  ws.send(
    JSON.stringify({
      type: 'step',
      step: `Creating project: ${projectName}`,
      status: 'running',
    })
  );

  // Initialize project
  const initResult = await sandbox.initProject(projectName, template as any);

  ws.send(
    JSON.stringify({
      type: 'project_created',
      projectName,
      files: initResult.files,
    })
  );

  // Generate files
  const filesToCreate = plan.files;
  const totalFiles = filesToCreate.length;
  const existingFiles: Record<string, string> = {};

  ws.send(JSON.stringify({ type: 'phase', phase: 'writing' }));

  for (let i = 0; i < filesToCreate.length; i++) {
    const fileInfo = filesToCreate[i];
    const filePath = fileInfo.path;
    const fileDesc = fileInfo.description;

    if (!filePath) continue;

    ws.send(JSON.stringify({ type: 'file_start', file: filePath }));

    const progress = 10 + Math.floor(((i + 1) / totalFiles) * 80);
    ws.send(JSON.stringify({ type: 'progress', progress }));
    ws.send(
      JSON.stringify({
        type: 'step',
        step: `Generating ${filePath}`,
        status: 'running',
      })
    );

    let content = '';
    for await (const chunk of coder.generateFile({
      goal,
      filePath,
      description: fileDesc,
      existingFiles,
    })) {
      content += chunk;
      ws.send(
        JSON.stringify({
          type: 'file_chunk',
          file: filePath,
          chunk,
        })
      );
    }

    // Save file
    await sandbox.writeProjectFile(projectName, filePath, content);
    existingFiles[filePath] = content;

    ws.send(
      JSON.stringify({
        type: 'file_complete',
        file: filePath,
        content,
      })
    );

    ws.send(
      JSON.stringify({
        type: 'step',
        step: `Generated ${filePath}`,
        status: 'done',
      })
    );
  }

  ws.send(JSON.stringify({ type: 'progress', progress: 100 }));
  ws.send(JSON.stringify({ type: 'phase', phase: 'complete' }));

  ws.send(
    JSON.stringify({
      type: 'done',
      taskId,
      mode: 'code',
      result: {
        success: true,
        projectName,
        previewUrl: `/sandbox/${projectName}/index.html`,
        files: Object.keys(existingFiles),
      },
    })
  );
}

/**
 * Run research (simplified placeholder)
 */
async function runResearch(ws: any, taskId: string, goal: string, planner: Planner) {
  ws.send(JSON.stringify({ type: 'phase', phase: 'planning' }));
  ws.send(JSON.stringify({ type: 'progress', progress: 10 }));

  // Create plan
  const plan = await planner.createPlan(goal);

  ws.send(
    JSON.stringify({
      type: 'step',
      step: `Created ${plan.length} steps`,
      status: 'done',
    })
  );

  // For now, just generate a basic report
  ws.send(JSON.stringify({ type: 'phase', phase: 'writing' }));
  ws.send(JSON.stringify({ type: 'progress', progress: 50 }));

  const report = await planner.generateReport(goal, [], [], 'overview');

  ws.send(JSON.stringify({ type: 'progress', progress: 100 }));
  ws.send(JSON.stringify({ type: 'phase', phase: 'complete' }));

  ws.send(
    JSON.stringify({
      type: 'done',
      taskId,
      mode: 'research',
      result: {
        success: true,
        runId: taskId,
        report,
      },
    })
  );
}

// Serve sandbox files
app.use(
  '/sandbox/*',
  serveStatic({
    root: join(__dirname, '../../..', 'sandbox_workspace'),
    rewriteRequestPath: (path) => path.replace('/sandbox', ''),
  })
);

// Start server
const port = parseInt(process.env.PORT || '8088');

console.log(`[Monus] Starting server on port ${port}...`);

const server = serve(
  {
    fetch: app.fetch,
    port,
  },
  (info) => {
    console.log(`[Monus] Server running at http://localhost:${info.port}`);
  }
);

injectWebSocket(server);
