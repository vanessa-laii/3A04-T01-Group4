import { Image } from 'expo-image';
import { Platform, StyleSheet, View } from 'react-native';

import { Collapsible } from '@/components/ui/collapsible';
import { ExternalLink } from '@/components/external-link';
import ParallaxScrollView from '@/components/parallax-scroll-view';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Fonts } from '@/constants/theme';

import { useFonts, Inter_400Regular, Inter_700Bold } from "@expo-google-fonts/inter";
import { SpaceGrotesk_400Regular, SpaceGrotesk_700Bold } from "@expo-google-fonts/space-grotesk";

// 1. Import your image from the assets folder
const MapImage = require('@/assets/images/map_image.png');

export default function TabTwoScreen() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_700Bold,
    SpaceGrotesk_400Regular,
    SpaceGrotesk_700Bold
  });

  return (
    <ParallaxScrollView 
      headerBackgroundColor={{ light: '#D0D0D0', dark: '#353636' }}
      headerImage={
        // 2. Added explicit container if needed, but Image must have size
        <Image
          source={MapImage}
          style={styles.headerImage}
          contentFit="cover" // "cover", "contain", "fill"
        />
      }>
      <ThemedView style={styles.titleContainer}>
        <ThemedText
          type="title"
          style={{
                fontFamily: 'SpaceGrotesk_700Bold',
          }}>
          Help Page
        </ThemedText>
      </ThemedView>
      <ThemedText style={styles.ThemedText}>View frequently asked questions about the  <ThemedText style={{fontFamily: 'Inter_700Bold'}} >SCEMAS</ThemedText> app
      </ThemedText>
      <Collapsible title="System Information" >
        <ThemedText style={styles.ThemedText}>
          The <ThemedText style={{fontFamily: 'Inter_700Bold'}}>SCEMAS Citizen City Alerts</ThemedText> app uses a smart-city environmental monitoring system to give citizens real-time alerts on hazardous events within their communities.

          {/*{' '}
          <ThemedText style={{fontFamily: 'Inter_700Bold'}}>app/(tabs)/index.tsx</ThemedText> and{' '}
          <ThemedText style={{fontFamily: 'Inter_700Bold'}}>app/(tabs)/explore.tsx</ThemedText>
        </ThemedText>
        <ThemedText>
          The layout file in <ThemedText style={{fontFamily: 'Inter_700Bold'}}>app/(tabs)/_layout.tsx</ThemedText>{' '}
          sets up the tab navigator.*/}
        </ThemedText>

        {/*
        <ExternalLink href="https://docs.expo.dev/router/introduction">
          <ThemedText type="link">Learn more</ThemedText>
        </ExternalLink>*/}
      </Collapsible>
      <Collapsible title="How to use">
        <ThemedText style={styles.ThemedText}>
          On the <ThemedText style={{fontFamily: 'Inter_700Bold'}}>Home</ThemedText> page of the application, enter your address and press the <ThemedText style={{fontFamily: 'Inter_700Bold'}}>Start</ThemedText> button. This will take you to the map view of your city, where <ThemedText style={{fontFamily: 'Inter_700Bold'}}>alerts</ThemedText> are represented by white circles. Alert details can be viewed by pressing on the alert of interest.
        </ThemedText>
      </Collapsible>

      <Collapsible title="Compatibility">
        <ThemedText style={styles.ThemedText}>
          This application can be used on both <ThemedText style={{fontFamily: 'Inter_700Bold'}}>IOS</ThemedText> and <ThemedText style={{fontFamily: 'Inter_700Bold'}}>Android</ThemedText> devices
        </ThemedText>
      </Collapsible>

      <Collapsible title="About">
        <ThemedText style={styles.ThemedText}>
         This application was developed using <ThemedText style={{fontFamily: 'Inter_700Bold'}}>React Native</ThemedText> and <ThemedText style={{fontFamily: 'Inter_700Bold'}}>Expo</ThemedText> frameworks and templates.   
        </ThemedText>

        <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center', marginTop:10, marginLeft:25}}>
          <Image
            source={require('@/assets/images/react-logo.png')}
            style={{ width: 100, height: 100, alignSelf: 'center' }}
          />
          <Image
            source={require('@/assets/images/android-icon-foreground.png')}
            style={{ width: 180, height: 100, alignSelf: 'center' }}
          />
        </View>

        <ExternalLink href="https://github.com/vanessa-laii/3A04-T01-Group4">
          <ThemedText style={styles.ThemedText} type="link">Visit the GitHub page</ThemedText>
        </ExternalLink>
      </Collapsible>

      <Collapsible title="Contact">
        <ThemedText style={styles.ThemedText}>
          For further questions or concerns, contact us at <ThemedText style={{fontFamily: 'Inter_700Bold'}}>Placeholder@gmail.com</ThemedText>
          </ThemedText>
      </Collapsible>
    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
  headerImage: {
    width: '100%',    // Essential
    height: 250,      // Essential
    bottom: 0,
    left: 0,
    position: 'absolute',
  },
  titleContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  ThemedText: {
    fontFamily: 'Inter_400Regular'
  }
});
