import React from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE } from 'react-native-maps';

const INITIAL_REGION = {
  latitude: 43.2580,
  longitude: -79.9180,
  latitudeDelta: 0.3,
  longitudeDelta: 0.3,
};

export default function MapScreen() {
  return (
    <View style={{ flex:1 }}>
      <MapView
        style={StyleSheet.absoluteFill}
        provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined}
        initialRegion={INITIAL_REGION}
      >
        <Marker
          coordinate={{ latitude: INITIAL_REGION.latitude, longitude: INITIAL_REGION.longitude }}
          title="SCEMAS"
          description="Initial region"
        />
      </MapView>
    </View>
  );
}