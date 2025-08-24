// Type definitions for external libraries

// file-saver now has official types installed

// jsPDF already has type definitions

declare module 'html2canvas' {
  interface Html2CanvasOptions {
    scale?: number;
    useCORS?: boolean;
    allowTaint?: boolean;
  }
  
  function html2canvas(element: HTMLElement, options?: Html2CanvasOptions): Promise<HTMLCanvasElement>;
  export default html2canvas;
}

declare module 'xlsx' {
  interface WorkSheet {
    [key: string]: any;
  }
  
  interface WorkBook {
    Sheets: { [key: string]: WorkSheet };
    SheetNames: string[];
  }
  
  export const utils: {
    json_to_sheet(data: any[]): WorkSheet;
    book_new(): WorkBook;
    book_append_sheet(workbook: WorkBook, worksheet: WorkSheet, name?: string): void;
  };
  
  export function write(workbook: WorkBook, options: { bookType: string; type: string }): any;
}

declare module 'chart.js' {
  export interface ChartConfiguration {
    type: ChartType;
    data: any;
    options?: any;
  }
  
  export type ChartType = 'line' | 'bar' | 'pie' | 'doughnut' | 'area';
  
  export class Chart {
    constructor(ctx: any, config: ChartConfiguration);
    destroy(): void;
    static register(...items: any[]): void;
  }
  
  export const registerables: any[];
}