import * as React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

// Import screens
import HomeScreen from './screens/HomeScreen';
import ScanScreen from './screens/ScanScreen';
import ChapterAssignScreen from './screens/ChapterAssignScreen';
import ResultsScreen from './screens/ResultsScreen';
import ReviewScreen from './screens/ReviewScreen';

// Define the navigation stack parameter list
export type RootStackParamList = {
  Home: undefined;
  Scan: undefined;
  ChapterAssign: { sections: string[] };
  Results: { 
    chapterAssignments: {
      section: number;
      year: number;
      season: string;
      subject: string;
      part: string;
    }[],
    answers: Record<string, string[]>
  };
  Review: { 
    mistakes: {
      chapter: number;
      question: number;
      userAnswer: string;
      correctAnswer: string;
      subject: string;
    }[]
  };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator initialRouteName="Home">
          <Stack.Screen 
            name="Home" 
            component={HomeScreen} 
            options={{ title: 'Psychometric Exam Scanner' }} 
          />
          <Stack.Screen 
            name="Scan" 
            component={ScanScreen} 
            options={{ title: 'Scan Answer Sheet' }} 
          />
          <Stack.Screen 
            name="ChapterAssign" 
            component={ChapterAssignScreen} 
            options={{ title: 'Assign Chapters' }} 
          />
          <Stack.Screen 
            name="Results" 
            component={ResultsScreen} 
            options={{ title: 'Exam Results', headerBackVisible: false }} 
          />
          <Stack.Screen 
            name="Review" 
            component={ReviewScreen} 
            options={{ title: 'Review Mistakes' }} 
          />
        </Stack.Navigator>
        <StatusBar style="auto" />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
