import { View, Text, StyleSheet, TextInput, Button, Alert, Platform} from 'react-native'
import React from 'react'
import {SafeAreaView, SafeAreaProvider} from 'react-native-safe-area-context';
import MapView, {PROVIDER_GOOGLE} from 'react-native-maps';

const INITIAL_REGION = {
  latitude: 43.2580,
  longitude: -79.9180,
  latitudeDelta: 0.3,
  longitudeDelta: 0.3
}

export default function App() {
  return (
    <View style={{ flex:1 }}>
      <MapView
        style={StyleSheet.absoluteFill}
        provider={PROVIDER_GOOGLE}
        initialRegion={INITIAL_REGION}
        />
    </View>
  );
}