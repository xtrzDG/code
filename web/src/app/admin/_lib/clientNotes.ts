/**
 * The platform team's notes about a client: what a note accepts (1 to
 * 2,000 characters, as the API's `ClientNoteText`) and whether it was
 * edited after it was written.
 */

export const NOTE_MAX = 2000;

/** The note as sent: no blanks around it. */
export function cleanNote(text: string): string {
  return text.trim();
}

export function isNoteValid(text: string): boolean {
  const note = cleanNote(text);
  return note.length >= 1 && note.length <= NOTE_MAX;
}

/** Edited: changed more than a second after it was written (microseconds). */
export function isNoteEdited(note: { created_at: number; updated_at: number }): boolean {
  return note.updated_at - note.created_at > 1_000_000;
}
