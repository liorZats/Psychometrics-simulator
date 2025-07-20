
import { ChapterAssignment, ExamResults, Mistake, Subject } from './types';
import { getAnswerKey } from '../data/answerKeys';

// Calculate the exam results based on user answers and chapter assignments
export function calculateResults(
  chapterAssignments: ChapterAssignment[],
  userAnswers: Record<string, string[]>
): ExamResults {
  const mistakes: Mistake[] = [];
  const subjectScores: Record<Subject, { correct: number; total: number }> = {
    Math: { correct: 0, total: 0 },
    Hebrew: { correct: 0, total: 0 },
    English: { correct: 0, total: 0 }
  };
  
  // Process each chapter assignment
  chapterAssignments.forEach(assignment => {
    const { section, year, season, subject, part } = assignment;
    const sectionKey = `section${section}`;
    
    // Get user answers for this section
    const sectionAnswers = userAnswers[sectionKey] || [];
    
    // Get correct answers for this exam chapter
    const correctAnswers = getAnswerKey(year, season, subject, part);
    
    if (!correctAnswers) {
      console.warn(`No answer key found for ${year} ${season} ${subject} ${part}`);
      return;
    }
    
    // Compare answers and record mistakes
    sectionAnswers.forEach((answer, index) => {
      const correctAnswer = correctAnswers[index];
      
      // Update subject scores
      subjectScores[subject].total++;
      
      if (answer === correctAnswer) {
        subjectScores[subject].correct++;
      } else {
        // Record mistake
        mistakes.push({
          chapter: section,
          question: index + 1,
          userAnswer: answer,
          correctAnswer,
          subject
        });
      }
    });
  });
  
  // Calculate final scores
  const mathScore = calculateSubjectScore(subjectScores.Math);
  const hebrewScore = calculateSubjectScore(subjectScores.Hebrew);
  const englishScore = calculateSubjectScore(subjectScores.English);
  
  // Calculate total score (weighted average based on the psychometric exam formula)
  // This is a simplified version - the real formula might be more complex
  const totalScore = Math.round((mathScore + hebrewScore + englishScore) / 3 * 150);
  
  return {
    totalScore,
    subjectScores: {
      Math: mathScore,
      Hebrew: hebrewScore,
      English: englishScore
    },
    mistakes
  };
}

// Calculate score for a subject (0-100)
function calculateSubjectScore(
  subjectData: { correct: number; total: number }
): number {
  if (subjectData.total === 0) return 0;
  return Math.round((subjectData.correct / subjectData.total) * 100);
}
