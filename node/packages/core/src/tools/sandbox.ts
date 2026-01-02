/**
 * Sandbox Tool - Project scaffolding and file management
 * Uses @modern-fs/core for file operations
 */

import { mkdirp, rimraf, copy, exists, gracefulPromises } from '@modern-fs/core';

const { writeFile, readFile } = gracefulPromises;
import { join, dirname } from 'path';
import { readdir, stat } from 'fs/promises';
import { exec } from 'child_process';
import { promisify } from 'util';
import type { ProjectTemplate, FileInfo } from '../types/index.js';

const execAsync = promisify(exec);

export interface ProjectInfo {
  name: string;
  path: string;
  files: FileInfo[];
}

export interface CommandResult {
  success: boolean;
  stdout: string;
  stderr: string;
  code: number;
}

export interface DevServerInfo {
  port: number;
  url: string;
  pid?: number;
}

export class SandboxTool {
  private workspaceDir: string;

  constructor(workspaceDir?: string) {
    this.workspaceDir = workspaceDir ?? join(process.cwd(), 'sandbox_workspace');
  }

  /**
   * Initialize a new project with template
   */
  async initProject(name: string, template: ProjectTemplate): Promise<ProjectInfo> {
    const projectPath = join(this.workspaceDir, name);

    // Clean up if exists
    if (await exists(projectPath)) {
      await rimraf(projectPath);
    }

    // Create project directory
    await mkdirp(projectPath);

    // Initialize based on template
    switch (template) {
      case 'html':
        await this.initHTMLProject(projectPath);
        break;
      case 'vite-react':
        await this.initViteReactProject(projectPath);
        break;
      case 'vite-vue':
        await this.initViteVueProject(projectPath);
        break;
      case 'node':
        await this.initNodeProject(projectPath);
        break;
      case 'python':
        await this.initPythonProject(projectPath);
        break;
    }

    return {
      name,
      path: projectPath,
      files: await this.listFiles(name),
    };
  }

  /**
   * Initialize HTML project
   */
  private async initHTMLProject(projectPath: string): Promise<void> {
    const indexHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monus App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="app">
        <h1>Hello Monus!</h1>
    </div>
    <script src="script.js"></script>
</body>
</html>`;

    const styleCss = `* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

#app {
    text-align: center;
}

h1 {
    font-size: 3rem;
    background: linear-gradient(90deg, #00d9ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}`;

    const scriptJs = `// Monus Generated App
console.log('Monus App Started!');

document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    // Your code here
});`;

    await writeFile(join(projectPath, 'index.html'), indexHtml);
    await writeFile(join(projectPath, 'style.css'), styleCss);
    await writeFile(join(projectPath, 'script.js'), scriptJs);
  }

  /**
   * Initialize Vite + React project
   */
  private async initViteReactProject(projectPath: string): Promise<void> {
    await mkdirp(join(projectPath, 'src'));
    await mkdirp(join(projectPath, 'public'));

    const packageJson = {
      name: projectPath.split(/[\\/]/).pop(),
      private: true,
      version: '0.0.0',
      type: 'module',
      scripts: {
        dev: 'vite',
        build: 'vite build',
        preview: 'vite preview',
      },
      dependencies: {
        react: '^18.2.0',
        'react-dom': '^18.2.0',
      },
      devDependencies: {
        '@vitejs/plugin-react': '^4.2.0',
        vite: '^5.0.0',
      },
    };

    const viteConfig = `import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})`;

    const indexHtml = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Monus App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>`;

    const mainJsx = `import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)`;

    const appJsx = `import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <h1>Monus App</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
      </div>
    </div>
  )
}

export default App`;

    const indexCss = `:root {
  font-family: Inter, system-ui, sans-serif;
  background: #242424;
  color: rgba(255, 255, 255, 0.87);
}

body {
  margin: 0;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.app {
  text-align: center;
}

button {
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  background-color: #1a1a1a;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}`;

    await writeFile(join(projectPath, 'package.json'), JSON.stringify(packageJson, null, 2));
    await writeFile(join(projectPath, 'vite.config.js'), viteConfig);
    await writeFile(join(projectPath, 'index.html'), indexHtml);
    await writeFile(join(projectPath, 'src', 'main.jsx'), mainJsx);
    await writeFile(join(projectPath, 'src', 'App.jsx'), appJsx);
    await writeFile(join(projectPath, 'src', 'index.css'), indexCss);
  }

  /**
   * Initialize Vite + Vue project
   */
  private async initViteVueProject(projectPath: string): Promise<void> {
    await mkdirp(join(projectPath, 'src'));

    const packageJson = {
      name: projectPath.split(/[\\/]/).pop(),
      private: true,
      version: '0.0.0',
      type: 'module',
      scripts: {
        dev: 'vite',
        build: 'vite build',
        preview: 'vite preview',
      },
      dependencies: {
        vue: '^3.4.0',
      },
      devDependencies: {
        '@vitejs/plugin-vue': '^5.0.0',
        vite: '^5.0.0',
      },
    };

    const viteConfig = `import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})`;

    const indexHtml = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Monus App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>`;

    const mainJs = `import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')`;

    const appVue = `<script setup>
import { ref } from 'vue'

const count = ref(0)
</script>

<template>
  <div class="app">
    <h1>Monus App</h1>
    <div class="card">
      <button @click="count++">count is {{ count }}</button>
    </div>
  </div>
</template>

<style scoped>
.app {
  text-align: center;
}
</style>`;

    const styleCss = `:root {
  font-family: Inter, system-ui, sans-serif;
  background: #242424;
  color: rgba(255, 255, 255, 0.87);
}

body {
  margin: 0;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

button {
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  background-color: #1a1a1a;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}`;

    await writeFile(join(projectPath, 'package.json'), JSON.stringify(packageJson, null, 2));
    await writeFile(join(projectPath, 'vite.config.js'), viteConfig);
    await writeFile(join(projectPath, 'index.html'), indexHtml);
    await writeFile(join(projectPath, 'src', 'main.js'), mainJs);
    await writeFile(join(projectPath, 'src', 'App.vue'), appVue);
    await writeFile(join(projectPath, 'src', 'style.css'), styleCss);
  }

  /**
   * Initialize Node.js project
   */
  private async initNodeProject(projectPath: string): Promise<void> {
    await mkdirp(join(projectPath, 'src'));

    const packageJson = {
      name: projectPath.split(/[\\/]/).pop(),
      version: '1.0.0',
      type: 'module',
      main: 'src/index.js',
      scripts: {
        start: 'node src/index.js',
        dev: 'node --watch src/index.js',
      },
    };

    const indexJs = `// Monus Generated Node.js App
console.log('Hello from Monus!');

async function main() {
  // Your code here
}

main().catch(console.error);`;

    await writeFile(join(projectPath, 'package.json'), JSON.stringify(packageJson, null, 2));
    await writeFile(join(projectPath, 'src', 'index.js'), indexJs);
  }

  /**
   * Initialize Python project
   */
  private async initPythonProject(projectPath: string): Promise<void> {
    const mainPy = `"""
Monus Generated Python App
"""

def main():
    print("Hello from Monus!")

if __name__ == "__main__":
    main()`;

    await writeFile(join(projectPath, 'main.py'), mainPy);
    await writeFile(join(projectPath, 'requirements.txt'), '');
  }

  /**
   * Write file to project
   */
  async writeProjectFile(projectName: string, filePath: string, content: string): Promise<void> {
    const fullPath = join(this.workspaceDir, projectName, filePath);

    // Ensure parent directory exists
    await mkdirp(dirname(fullPath));

    await writeFile(fullPath, content);
  }

  /**
   * Read file from project
   */
  async readProjectFile(projectName: string, filePath: string): Promise<string> {
    const fullPath = join(this.workspaceDir, projectName, filePath);
    return await readFile(fullPath, 'utf-8');
  }

  /**
   * Delete file from project
   */
  async deleteProjectFile(projectName: string, filePath: string): Promise<void> {
    const fullPath = join(this.workspaceDir, projectName, filePath);
    await rimraf(fullPath);
  }

  /**
   * List files in project
   */
  async listFiles(projectName: string, subPath = ''): Promise<FileInfo[]> {
    const projectPath = join(this.workspaceDir, projectName, subPath);

    if (!(await exists(projectPath))) {
      return [];
    }

    const files: FileInfo[] = [];
    const entries = await readdir(projectPath);

    for (const entry of entries) {
      if (entry.startsWith('.') || entry === 'node_modules') {
        continue;
      }

      const entryPath = join(projectPath, entry);
      const relativePath = subPath ? `${subPath}/${entry}` : entry;
      const stats = await stat(entryPath);

      if (stats.isDirectory()) {
        files.push({ path: relativePath, type: 'directory' });
        const subFiles = await this.listFiles(projectName, relativePath);
        files.push(...subFiles);
      } else {
        files.push({
          path: relativePath,
          type: 'file',
          size: stats.size,
        });
      }
    }

    return files;
  }

  /**
   * Run command in project directory
   */
  async runCommand(projectName: string, command: string, timeout = 60000): Promise<CommandResult> {
    const projectPath = join(this.workspaceDir, projectName);

    if (!(await exists(projectPath))) {
      return {
        success: false,
        stdout: '',
        stderr: 'Project not found',
        code: 1,
      };
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        cwd: projectPath,
        timeout,
      });

      return {
        success: true,
        stdout,
        stderr,
        code: 0,
      };
    } catch (error: any) {
      return {
        success: false,
        stdout: error.stdout ?? '',
        stderr: error.stderr ?? error.message,
        code: error.code ?? 1,
      };
    }
  }

  /**
   * Install dependencies
   */
  async installDeps(projectName: string): Promise<CommandResult> {
    const projectPath = join(this.workspaceDir, projectName);

    // Check project type
    if (await exists(join(projectPath, 'package.json'))) {
      return await this.runCommand(projectName, 'npm install', 120000);
    } else if (await exists(join(projectPath, 'requirements.txt'))) {
      return await this.runCommand(projectName, 'pip install -r requirements.txt', 120000);
    }

    return {
      success: true,
      stdout: 'No dependencies to install',
      stderr: '',
      code: 0,
    };
  }

  /**
   * Start dev server
   */
  async startDevServer(projectName: string, port = 5173): Promise<DevServerInfo> {
    const projectPath = join(this.workspaceDir, projectName);

    let command: string;

    if (await exists(join(projectPath, 'package.json'))) {
      command = `npm run dev -- --port ${port}`;
    } else {
      // For HTML projects, use a simple HTTP server
      command = `npx serve -l ${port}`;
    }

    // Start in background (don't wait)
    exec(command, { cwd: projectPath });

    return {
      port,
      url: `http://localhost:${port}`,
    };
  }

  /**
   * Clean up project
   */
  async cleanup(projectName: string): Promise<void> {
    const projectPath = join(this.workspaceDir, projectName);
    await rimraf(projectPath);
  }

  /**
   * Get project path
   */
  getProjectPath(projectName: string): string {
    return join(this.workspaceDir, projectName);
  }
}
