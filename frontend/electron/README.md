# SCEMAS Desktop App (Electron)

This directory contains the Electron configuration to package the SCEMAS web app as a Windows .exe desktop application.

## Setup

### Prerequisites
- Node.js 18+
- npm or yarn

### Install Dependencies
```bash
npm install
```

## Development

### Run in Web Mode
```bash
npm run dev
```
Navigate to `http://localhost:5173` in your browser.

### Run in Electron Development Mode
In one terminal, start the Vite dev server:
```bash
npm run dev
```

In another terminal, start the Electron app:
```bash
npm run dev:electron
```

The Electron app will open with hot module reloading enabled. DevTools will automatically open.

## Build & Package

### Build the Web App
```bash
npm run build
```

This creates optimized production files in the `dist/` directory.

### Build the .exe Installer
```bash
npm run build:electron
```

This will:
1. Compile TypeScript
2. Build the React app with Vite
3. Package everything into an Electron app
4. Create Windows installers (.exe and portable)

The generated installers will be in the `dist/` directory:
- `SCEMAS Setup X.X.X.exe` - NSIS installer (recommended)
- `SCEMAS X.X.X.exe` - Portable executable (no installation needed)

## Important Notes

### Supabase Auth
- Supabase authentication works seamlessly in Electron since it's HTTP-based
- No special configuration needed - your existing auth code will work as-is
- CORS should be configured in your Supabase project to allow `file://` protocol or `localhost`

### File Structure
```
frontend/
├── src/                    # React app source code
├── electron/              # Electron configuration
│   ├── main.ts           # Electron main process
│   └── preload.ts        # Preload script for secure IPC
├── dist/                  # Build output (generated)
└── package.json
```

### Security
- Context isolation is enabled (`contextIsolation: true`)
- Node integration is disabled (`nodeIntegration: false`)
- The preload script safely exposes only necessary APIs
- Communication between renderer and main process uses IPC

## Customization

### Application Icon
Place your app icon as `icon.png` (512x512) in the `assets/` directory. electron-builder will automatically generate the required icon formats.

### Window Size
Edit `electron/main.ts` - look for the `createWindow()` function to adjust initial width/height and minimum dimensions.

### Menu Items
Customize the application menu in `electron/main.ts` - modify the `template` array before calling `Menu.buildFromTemplate()`.

## Troubleshooting

### App won't start
- Ensure all dependencies are installed: `npm install`
- Try deleting `node_modules` and `dist` directories, then reinstalling

### Supabase not working
- Check your Supabase client URL is correct
- Verify CORS settings in Supabase dashboard
- Dev Tools will show network errors - check the Network tab

### Build fails
- Ensure `dist/` folder exists and contains `index.html`
- Check that all TypeScript files compile: `npx tsc`
- On Windows, you may need Visual C++ redistributable installed for building native modules

## References

- [Electron Documentation](https://www.electronjs.org/docs)
- [Electron Builder](https://www.electron.build/)
- [Vite + React](https://vitejs.dev/guide/#scaffolding-your-first-vite-project)
