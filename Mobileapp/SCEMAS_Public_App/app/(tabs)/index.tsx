import { View, Text, StyleSheet, TextInput, Button, Alert, Platform} from 'react-native'
import React from 'react'
import {SafeAreaView, SafeAreaProvider} from 'react-native-safe-area-context';

const app = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.titletext}>SCEMAS</Text>
      <Text style={styles.headertext}>Citizen City Alerts</Text>
      <Text style={styles.bodytext}>Enter your location</Text>
      <SafeAreaProvider>
        <SafeAreaView>
          <TextInput 
            style={styles.input} 
            placeholder='City, State, Country'>
          </TextInput>
                <Button title="start" color='#292732'>Start</Button>
        </SafeAreaView>
      </SafeAreaProvider>

    </View>
  )
}
export default app

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#d8d6ceff',
    flex: 1,
    flexDirection: 'column',
  },
  bodytext:{
    marginTop:80,
    color: '#292732',
    fontSize: 18,
    fontWeight: 'normal',
    textAlign: 'center',
  },
  titletext:{
    marginTop: 140,
    color: '#292732',
    fontSize: 60,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  headertext:{
    color: '#292732',
    fontSize: 32,
    fontWeight: 'medium',
    textAlign: 'center',
  },
  input:{    
    justifyContent: 'center',
    color: '#d8d6ceff',
    backgroundColor: '#292732',
    height: 40,
    width: 250,
    margin: 12,
    marginRight: 50,
    marginLeft: 70, 
    borderWidth: 1,
    padding: 10,
    borderCurve: 'circular',
    borderRadius: 15,
      fontSize: 16,
  },
  start:{    
    justifyContent: 'center',
    color: '#d8d6ceff',
    backgroundColor: '#292732',
    height: 40,
    width: 10,
    margin: 12,
    marginRight: 50,
    marginLeft: 70, 
    borderWidth: 1,
    padding: 10,
    borderCurve: 'circular',
    borderRadius: 15,
    fontSize: 16,
  }
})