/* eslint-disable */
import * as Router from 'expo-router';

export * from 'expo-router';

declare module 'expo-router' {
  export namespace ExpoRouter {
    export interface __routes<T extends string = string> extends Record<string, unknown> {
      StaticRoutes: `/` | `/(auth)` | `/(auth)/onboarding` | `/(auth)/sign-in` | `/(tabs)` | `/(tabs)/` | `/(tabs)/alerts` | `/(tabs)/me` | `/(tabs)/portfolio` | `/(tabs)/research` | `/_sitemap` | `/add-position` | `/alerts` | `/compare` | `/create-portfolio` | `/me` | `/onboarding` | `/portfolio` | `/research` | `/sign-in`;
      DynamicRoutes: `/ticker/${Router.SingleRoutePart<T>}`;
      DynamicRouteTemplate: `/ticker/[symbol]`;
    }
  }
}
