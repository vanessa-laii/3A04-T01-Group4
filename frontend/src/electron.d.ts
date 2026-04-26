export interface ElectronAPI {
  platform: string;
  versions: {
    electron: string;
    chrome: string;
    node: string;
  };
}

declare global {
  interface Window {
    electron: ElectronAPI;
  }
}
