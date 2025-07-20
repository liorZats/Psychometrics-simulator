
// Exam related types
export type Season = 'Winter' | 'Spring' | 'Summer' | 'Autumn';
export type Subject = 'Math' | 'Hebrew' | 'English';
export type Part = 'A' | 'B';

export interface ChapterAssignment {
  section: number;
  year: number;
  season: Season;
  subject: Subject;
  part: Part;
}

export interface ExamChapter {
  year: number;
  season: Season;
  subject: Subject;
  part: Part;
  answers: string[];
}

export interface Mistake {
  chapter: number;
  question: number;
  userAnswer: string;
  correctAnswer: string;
  subject: Subject;
}

export interface ExamResults {
  totalScore: number;
  subjectScores: {
    Math: number;
    Hebrew: number;
    English: number;
  };
  mistakes: Mistake[];
}

// UI related types
export interface ScanResult {
  sections: string[];
  answers: Record<string, string[]>;
}
