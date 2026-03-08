export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export class Logger {
  private static instance: Logger;
  private level: LogLevel;
  private isDisabled: boolean;

  private constructor() {
    this.level = this.getLogLevelFromEnv();
    this.isDisabled = process.env.EXOSPHERE_DISABLE_DEFAULT_LOGGING === 'true';
  }

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private getLogLevelFromEnv(): LogLevel {
    const levelName = (process.env.EXOSPHERE_LOG_LEVEL || 'INFO').toUpperCase();
    switch (levelName) {
      case 'DEBUG': return LogLevel.DEBUG;
      case 'INFO': return LogLevel.INFO;
      case 'WARN': return LogLevel.WARN;
      case 'ERROR': return LogLevel.ERROR;
      default: return LogLevel.INFO;
    }
  }

  private shouldLog(level: LogLevel): boolean {
    return !this.isDisabled && level >= this.level;
  }

  private formatMessage(level: string, name: string, message: string): string {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    return `${timestamp} | ${level} | ${name} | ${message}`;
  }

  public debug(name: string, message: string): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      console.debug(this.formatMessage('DEBUG', name, message));
    }
  }

  public info(name: string, message: string): void {
    if (this.shouldLog(LogLevel.INFO)) {
      console.info(this.formatMessage('INFO', name, message));
    }
  }

  public warn(name: string, message: string): void {
    if (this.shouldLog(LogLevel.WARN)) {
      console.warn(this.formatMessage('WARN', name, message));
    }
  }

  public error(name: string, message: string): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      console.error(this.formatMessage('ERROR', name, message));
    }
  }
}

export const logger = Logger.getInstance();
