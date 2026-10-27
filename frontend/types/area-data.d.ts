// The package exports its runtime entry without exposing its bundled .d.ts
// through the exports map. Keep the published areaList shape available to TS.
declare module "@vant/area-data" {
  export const areaList: {
    province_list: Record<string, string>;
    city_list: Record<string, string>;
    county_list: Record<string, string>;
  };
}
