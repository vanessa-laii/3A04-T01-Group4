import React from 'react';
import { Platform, StyleSheet, View, Text, useColorScheme } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE, Callout } from 'react-native-maps';
import { useFonts, Inter_400Regular } from '@expo-google-fonts/inter';
import { SpaceGrotesk_700Bold } from '@expo-google-fonts/space-grotesk';
import { Background } from '@react-navigation/elements';
import { Stack } from 'expo-router';

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
    SpaceGrotesk_700Bold,
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
        },
        calloutBubble: {
          backgroundColor: isDarkMode ? '#fff' : '#2d2d33ff',
          borderColor: isDarkMode ? '#52525b' : '#d4d4d8',
        },
        arrowBorder: {
          borderTopColor: isDarkMode ? '#fff' : '#2d2d33ff',
        }
    };

  if (!fontsLoaded) {
    return null; // Or a loading component
  }

  return (
    <>
    <Stack.Screen options={{ headerBackButtonDisplayMode: 'minimal' }} />
    
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
            calloutOffset={{ x: 0, y: 12}}
          >
            {/* Custom Marker View */}
            <View style={styles.markerWrapper}>
              <View style={[styles.circle, themeStyles.circle]} />
            </View>

            <Callout tooltip={true}>
              <View>
              <View style={[styles.calloutBubble, themeStyles.calloutBubble]}>
                <Text style={[styles.calloutTitle, { color: isDarkMode ? '#000' : '#fff' }]}>
                  {marker.title}
                </Text>
                <Text style={[styles.calloutDescription, { color: isDarkMode ? '#52525b' : '#d4d4d8' }]}>
                  {marker.description}
                </Text>
              </View>
                  
                  <View style={[styles.arrow, themeStyles.arrowBorder]} />

              </View>
            </Callout>

          </Marker>
        ))}
      </MapView>
    </View>
    </>
  );
}

const styles = StyleSheet.create({
  markerWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  circle: {
    width: 19,
    height: 19,
    borderRadius: 15,
    backgroundColor: '#d4d4d8', 
    borderWidth: 2,
    borderColor: '#fff',
  },
  calloutBubble: {
    width: 200,
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: 'column',
    justifyContent: 'center',

  },
  calloutTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    fontFamily: 'SpaceGrotesk_700Bold',
    marginBottom: 2,
  },
  calloutDescription: {
    fontSize: 12,
    fontFamily: 'Inter_400Regular',
  },
  arrow: {
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderWidth: 10,
    borderTopColor: '#fff', // Change to match bubble background
    alignSelf: 'center',
    marginTop: -1, // Adjust to make it sit under the bubble
  },
});
