import React from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE} from 'react-native-maps';
import { useFonts, Inter_400Regular } from "@expo-google-fonts/inter";
import { SpaceGrotesk_400Regular } from "@expo-google-fonts/space-grotesk";

const INITIAL_REGION = {
  latitude: 43.2580,
  longitude: -79.9180,
  latitudeDelta: 0.3,
  longitudeDelta: 0.1,
};

export default function MapScreen() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    SpaceGrotesk_400Regular,
  });

  return (
    <View style={{ flex:1, }}>
      <MapView
        style={StyleSheet.absoluteFill}
        provider={Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined}
        initialRegion={INITIAL_REGION}
        mapType='mutedStandard'
      >
        <Marker
          coordinate={{ latitude: INITIAL_REGION.latitude, longitude: INITIAL_REGION.longitude }}
          title="PM2.5 above threshold"
          description="Zone C - 41 ug/m"
        >
            
          {/* Custom Marker View goes here */}
          <View style={styles.markerWrapper}>
            <View style={styles.circle} />
          </View>
        </Marker>

        <Marker
          coordinate={{ latitude: 43.23, longitude: -79.880 }}
          title="UV Index Critically High"
          description="Zone A - 11.2 UV"
        >
          {/* Custom Marker View goes here */}
          <View style={styles.markerWrapper}>
            <View style={styles.circle} />
          </View>
        </Marker>

        <Marker
          coordinate={{ latitude: 43.25, longitude: -79.880 }}
          title="Temperature Spike detected"
          description="Zone B - 38.4 C"
        >
          {/* Custom Marker View goes here */}
          <View style={styles.markerWrapper}>
            <View style={styles.circle} />
          </View>
        </Marker>

      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  alerts: {flex: 1, fontFamily: 'Inter_400Regular'},
  markerWrapper: { alignItems: 'center', justifyContent: 'center', textAlign: 'center' },
  circle: {
    width: 17, height: 17,
    borderRadius: 15,
    backgroundColor: '#ffffffff',
    borderWidth: 2, borderColor: '#fff'
  },
  text: { color: '#fff', fontWeight: 'bold' }
});