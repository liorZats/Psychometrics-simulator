
# Psychometric Exam Scanner App

A mobile application designed to help students simulate and evaluate the Israeli psychometric exam. The app allows users to scan their completed answer sheets and automatically evaluate their test performance.

## Features

### Answer Sheet Scanning
- Scan completed answer sheets using the device camera
- Automatic detection and segmentation of the answer sheet into 8 sections

### Exam Chapter Assignment
- Assign each section to a specific exam chapter
- Select year (2000-2025), season (Winter, Spring, Summer, Autumn), subject (Math, Hebrew, English), and chapter part (A or B)

### Evaluation
- Automatic comparison of student answers against correct answers
- Calculation of total score and per-subject performance
- Detailed mistake analysis

### Results Display
- Overall psychometric score (200-800 scale)
- Breakdown by subject (Math, Hebrew, English)
- Mistake summary by chapter and topic
- Option to review incorrect answers in detail

## Technical Implementation

### Technologies Used
- React Native with Expo
- TypeScript for type safety
- Expo Camera for answer sheet scanning
- React Navigation for screen navigation

### Project Structure
- `App.tsx`: Main application entry point with navigation setup
- `screens/`: Main application screens
  - `HomeScreen.tsx`: Initial screen with scan button
  - `ScanScreen.tsx`: Camera screen for scanning answer sheets
  - `ChapterAssignScreen.tsx`: Screen for assigning chapters to scanned sections
  - `ResultsScreen.tsx`: Display of evaluation results
  - `ReviewScreen.tsx`: Detailed review of incorrect answers
- `utils/`: Utility functions
  - `types.ts`: TypeScript type definitions
  - `answerSheetParser.ts`: Logic for parsing answer sheets
  - `scoreCalculator.ts`: Logic for calculating scores
- `data/`: Mock data for testing
  - `answerKeys.ts`: Correct answers for each exam

## Future Enhancements
- Implement actual image processing for answer sheet detection
- Add user accounts to save test history
- Provide detailed explanations for correct answers
- Support for additional exam formats
- Performance analytics over time
