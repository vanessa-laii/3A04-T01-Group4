import React from 'react';
import { Platform, StyleSheet, View, Text, useColorScheme } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE } from 'react-native-maps';
import { useFonts, Inter_400Regular } from '@expo-google-fonts/inter';
import { SpaceGrotesk_400Regular } from '@expo-google-fonts/space-grotesk';

const INITIAL_REGION = {
  latitude: 43.2580,
  longitude: -79.9180,
  latitudeDelta: 0.3,
  longitudeDelta: 0.1,
};

export default function MapScreen() {
  const colorScheme = useColorScheme();
  const isDarkMode = colorScheme === 'dark';

  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    SpaceGrotesk_400Regular,
  });

  // 1. Data Generator Array
  const markerData = [
    {
      id: 1,
      title: 'PM2.5 above threshold',
      description: 'Zone C - 41 ug/m',
      lat: 43.2580,
      lng: -79.9180
    },
    {
      id: 2,
      title: 'UV Index Critically High',
      description: 'Zone A - 11.2 UV',
      lat: 43.23,
      lng: -79.880
    },
    {
      id: 3,
      title: 'Temperature Spike detected',
      description: 'Zone B - 38.4 C',
      lat: 43.25,
      lng: -79.880
    }
  ];

  const themeStyles = {
        circle: { 
            backgroundColor: isDarkMode ? '#d4d4d8' : '#71717a',
            borderColor: isDarkMode? '#fff' : '#3f3f46'
          }
    };

  if (!fontsLoaded) {
    return null; // Or a loading component
  }

  return (
    <View style={{ flex: 1 }}>
      <MapView
        style={StyleSheet.absoluteFill}
        provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined}
        initialRegion={INITIAL_REGION}
        mapType="mutedStandard"
      >
        {/* 2. Marker Generator: Map through the array */}
        {markerData.map((marker) => (
          <Marker
            key={marker.id} // Important for performance
            coordinate={{ latitude: marker.lat, longitude: marker.lng }}
            title={marker.title}
            description={marker.description}
          >
            {/* Custom Marker View */}
            <View style={styles.markerWrapper}>
              <View style={[styles.circle, themeStyles.circle]} />
            </View>
          </Marker>
        ))}
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  markerWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  circle: {
    width: 17,
    height: 17,
    borderRadius: 15,
    backgroundColor: '#d4d4d8', 
    borderWidth: 2,
    borderColor: '#fff',
  },
});
