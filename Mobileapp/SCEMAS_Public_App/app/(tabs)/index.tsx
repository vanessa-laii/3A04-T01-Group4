import { View, Text, StyleSheet, TextInput, Button, Alert, Platform} from 'react-native'
import React from 'react'
import {SafeAreaView, SafeAreaProvider} from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useFonts, Inter_400Regular } from "@expo-google-fonts/inter";
import { SpaceGrotesk_400Regular } from "@expo-google-fonts/space-grotesk";

function displayAlerts(){
  router.push('/Map');
}

const app = () => {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    SpaceGrotesk_400Regular,
  });
  
  return (
    <SafeAreaProvider>

    <View style={styles.container}>
      <Text style={styles.titletext}>SCEMAS</Text>
      <Text style={styles.headertext}>Citizen City Alerts</Text>

      <View style={styles.div}>
        </View>

      <View style={styles.startblock}>
        </View>
        
        <Text style={styles.bodytext}>Enter your location</Text>


          <TextInput 
            style={styles.input} 
            placeholder='City, State, Country'>
          </TextInput>
          <Button title="Start" color="#000000" onPress={displayAlerts} />



    </View>

    </SafeAreaProvider>
  )
}
export default app

const styles = StyleSheet.create({
  div: {
    backgroundColor: '#18181b',
    width: '75%',
    height: '23%',
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
    fontSize: 70,
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
    color: '#d8d6ceff',
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
    marginTop: 434,
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