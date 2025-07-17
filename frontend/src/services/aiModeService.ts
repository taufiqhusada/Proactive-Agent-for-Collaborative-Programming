/**
 * AI Mode Service - Manages different AI assistant modes
 * - Shared Mode: AI acts as a team collaborator visible to all users
 * - Individual Mode: AI acts as personal assistant for each user
 */

export enum AIMode {
  SHARED = 'shared',
  INDIVIDUAL = 'individual'
}

export interface AIModeSettings {
  mode: AIMode;
  roomId: string;
  userId: string;
}

export class AIModeService {
  private currentMode: AIMode = AIMode.SHARED;
  private roomId: string = '';
  private userId: string = '';
  private sessionStarted: boolean = false;
  private socket: any = null;

  setSocket(socket: any): void {
    this.socket = socket;
  }

  setSessionState(started: boolean): void {
    this.sessionStarted = started;
  }

  isSessionStarted(): boolean {
    return this.sessionStarted;
  }

  setMode(mode: AIMode, roomId: string, userId: string, broadcast: boolean = true): void {
    // Don't allow mode changes during active session
    if (this.sessionStarted && broadcast) {
      console.warn('Cannot change AI mode during active session');
      return;
    }

    const oldMode = this.currentMode;
    this.currentMode = mode;
    this.roomId = roomId;
    this.userId = userId;

    // Broadcast mode change to other users in the room
    if (broadcast && this.socket) {
      this.socket.emit('ai_mode_changed', {
        roomId: roomId,
        mode: mode,
        changedBy: userId
      });
    }

    console.log(`AI mode changed from ${oldMode} to ${mode} by user ${userId}`);
  }

  getCurrentMode(): AIMode {
    return this.currentMode;
  }

  isSharedMode(): boolean {
    return this.currentMode === AIMode.SHARED;
  }

  isIndividualMode(): boolean {
    return this.currentMode === AIMode.INDIVIDUAL;
  }

  getAIChannelName(): string {
    if (this.isIndividualMode()) {
      return `ai_individual_${this.userId}`;
    }
    return `ai_shared_${this.roomId}`;
  }

  getChatContext(): { mode: AIMode; channelName: string } {
    return {
      mode: this.currentMode,
      channelName: this.getAIChannelName()
    };
  }
}

// Global instance
export const aiModeService = new AIModeService();
