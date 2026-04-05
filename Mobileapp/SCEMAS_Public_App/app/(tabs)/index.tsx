import { View, Text, StyleSheet, TextInput, Button, Alert, Platform, useColorScheme} from 'react-native'
import React from 'react'
import {SafeAreaView, SafeAreaProvider} from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useFonts, Inter_400Regular } from "@expo-google-fonts/inter";
import { SpaceGrotesk_400Regular } from "@expo-google-fonts/space-grotesk";

function displayAlerts(){
  router.push('/Map');
}

const app = () => {
    const colorScheme = useColorScheme();
    const isDarkMode = colorScheme === 'dark';

    const [fontsLoaded] = useFonts({
        Inter_400Regular,
        SpaceGrotesk_400Regular,
  });
  
  const themeStyles = {
      container: { backgroundColor: isDarkMode ? '#000000' : '#ededf1ff' },
      text: { color: isDarkMode ? '#ffffff' : '#000000' },
      input: { 
          backgroundColor: isDarkMode ? '#27272a' : '#f4f4f5',
          color: isDarkMode ? '#bdbbb6' : '#18181b',
          borderColor: isDarkMode ? '#27272a' : '#e4e4e7'
      },
      startblock: {backgroundColor: isDarkMode ? '#d4d4d8': '#27272a'},
      div: { backgroundColor: isDarkMode ? '#18181b' : '#fdfdfdff' }
  };

  return (
    <SafeAreaProvider>
        {/* 3. Apply the dynamic styles using an array [static, dynamic] */}
        <View style={[styles.container, themeStyles.container]}>
            <Text style={[styles.titletext, themeStyles.text]}>SCEMAS</Text>
            <Text style={styles.headertext}>Citizen City Alerts</Text>
            
            <View style={[styles.div, themeStyles.div]} />
            <View style={[styles.startblock, themeStyles.startblock]} />
            
            <Text style={[styles.bodytext, { color: isDarkMode ? '#d4d4d8' : '#71717a' }]}>
                Enter your location
            </Text>
            
            <TextInput 
                style={[styles.input, themeStyles.input]} 
                placeholder='City, State, Country'
                placeholderTextColor={isDarkMode ? '#71717a' : '#a1a1aa'}
            />

            <View style={{ position: 'absolute', top: 438, left: 70, width: 250 }}>
                <Button 
                    title="Start" 
                    color={isDarkMode ? "#000000" : "#d4d4d8"} 
                    onPress={displayAlerts} 
                />
            </View>
        </View>
    </SafeAreaProvider>
  )
}
export default app

const styles = StyleSheet.create({
  div: {
    backgroundColor: '#18181b',
    width: '75%',
    height: '25%',
    marginTop: 320,
    marginLeft: 50,
    position: 'absolute',
    borderRadius: 10,
  },
  container: {
    backgroundColor: '#000000ff',
    flex: 1,
    flexDirection: 'column',
  },
  bodytext:{
    fontFamily: 'Inter_400Regular',
    marginTop:80,
    color: '#d4d4d8',
    fontSize: 18,
    fontWeight: 'normal',
    textAlign: 'center',
  },
  titletext:{
    fontFamily: 'SpaceGrotesk_400Regular',
    marginTop: 140,
    color: '#ffffffff',
    fontSize: 71,
    fontWeight: '300',
    textAlign: 'center',
  },
  headertext:{
    fontFamily: 'SpaceGrotesk_400Regular',
    color: '#71717a',
    fontSize: 32,
    fontWeight: 'medium',
    textAlign: 'center',
  },
  input:{    
    fontFamily: 'Inter_400Regular',
    justifyContent: 'center',
    color: '#bdbbb6ff',
    backgroundColor: '#27272a',
    height: 40,
    width: 250,
    margin: 12,
    marginTop: 15,
    marginRight: 50,
    marginLeft: 70, 
    borderWidth: 1,
    padding: 10,
    borderRadius: 10,
    borderColor: '#27272a',
    fontSize: 16,
  },
  startblock:{    
    fontFamily: 'Inter_400Regular',
    justifyContent: 'center',
    color: '#d8d6ceff',
    backgroundColor: '#d4d4d8',
    height: 30,
    width: 250,
    margin: 12,
    marginRight: 50,
    marginLeft: 70, 
    borderWidth: 1,
    padding: 10,
    borderRadius: 10,
    borderColor: '#d4d4d8',
    fontSize: 16,
    position: 'absolute',
    marginTop: 442,
  },
  start:{    
    fontFamily: 'SpaceGrotesk_400Regular',
    justifyContent: 'center',
    color: '#d8d6ceff',
    backgroundColor: '#292732',
    height: 40,
    width: 10,
    margin: 12,
    marginRight: 50,
    marginLeft: 50, 
    borderWidth: 1,
    padding: 10,
    borderCurve: 'circular',
    borderRadius: 15,
    fontSize: 16,
  },
  map:{
    height: '100%',
    width: 100,
  }
})