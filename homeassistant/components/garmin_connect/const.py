"""Constants for the Garmin Connect integration."""
from homeassistant.const import DEVICE_CLASS_TIMESTAMP

DOMAIN = "garmin_connect"
ATTRIBUTION = "Data provided by garmin.com"

GARMIN_ENTITY_LIST = {
    "totalSteps": ["Total Steps", "steps", "mdi:walk", None],
    "dailyStepGoal": ["Daily Step Goal", "steps", "mdi:walk", None],
    "totalKilocalories": ["Total KiloCalories", "kcal", "mdi:food", None],
    "activeKilocalories": ["Active KiloCalories", "kcal", "mdi:food", None],
    "bmrKilocalories": ["BMR KiloCalories", "kcal", "mdi:food", None],
    "consumedKilocalories": ["Consumed KiloCalories", "kcal", "mdi:food", None],
    "burnedKilocalories": ["Burned KiloCalories", "kcal", "mdi:food", None],
    "remainingKilocalories": ["Remaining KiloCalories", "kcal", "mdi:food", None],
    "netRemainingKilocalories": [
        "Net Remaining KiloCalories",
        "kcal",
        "mdi:food",
        None,
    ],
    "netCalorieGoal": ["Net Calorie Goal", "cal", "mdi:food", None],
    "totalDistanceMeters": ["Total Distance Mtr", "mtr", "mdi:walk", None],
    "wellnessStartTimeLocal": [
        "Wellness Start Time",
        "",
        "mdi:clock",
        DEVICE_CLASS_TIMESTAMP,
    ],
    "wellnessEndTimeLocal": [
        "Wellness End Time",
        "",
        "mdi:clock",
        DEVICE_CLASS_TIMESTAMP,
    ],
    "wellnessDescription": ["Wellness Description", "", "mdi:clock", None],
    "wellnessDistanceMeters": ["Wellness Distance Mtr", "mtr", "mdi:walk", None],
    "wellnessActiveKilocalories": [
        "Wellness Active KiloCalories",
        "kcal",
        "mdi:food",
        None,
    ],
    "wellnessKilocalories": ["Wellness KiloCalories", "kcal", "mdi:food", None],
    "highlyActiveSeconds": ["Highly Active Time", "minutes", "mdi:fire", None],
    "activeSeconds": ["Active Time", "minutes", "mdi:fire", None],
    "sedentarySeconds": ["Sedentary Time", "minutes", "mdi:seat", None],
    "sleepingSeconds": ["Sleeping Time", "minutes", "mdi:sleep", None],
    "measurableAwakeDuration": ["Awake Duration", "minutes", "mdi:sleep", None],
    "measurableAsleepDuration": ["Sleep Duration", "minutes", "mdi:sleep", None],
    "floorsAscendedInMeters": ["Floors Ascended Mtr", "mtr", "mdi:stairs", None],
    "floorsDescendedInMeters": ["Floors Descended Mtr", "mtr", "mdi:stairs", None],
    "floorsAscended": ["Floors Ascended", "floors", "mdi:stairs", None],
    "floorsDescended": ["Floors Descended", "floors", "mdi:stairs", None],
    "userFloorsAscendedGoal": ["Floors Ascended Goal", "floors", "mdi:stairs", None],
    "minHeartRate": ["Min Heart Rate", "bpm", "mdi:heart-pulse", None],
    "maxHeartRate": ["Max Heart Rate", "bpm", "mdi:heart-pulse", None],
    "restingHeartRate": ["Resting Heart Rate", "bpm", "mdi:heart-pulse", None],
    "minAvgHeartRate": ["Min Avg Heart Rate", "bpm", "mdi:heart-pulse", None],
    "maxAvgHeartRate": ["Max Avg Heart Rate", "bpm", "mdi:heart-pulse", None],
    "abnormalHeartRateAlertsCount": ["Abnormal HR Counts", "", "mdi:heart-pulse", None],
    "lastSevenDaysAvgRestingHeartRate": [
        "Last 7 Days Avg Heart Rate",
        "bpm",
        "mdi:heart-pulse",
        None,
    ],
    "averageStressLevel": ["Avg Stress Level", "", "mdi:flash-alert", None],
    "maxStressLevel": ["Max Stress Level", "", "mdi:flash-alert", None],
    "stressQualifier": ["Stress Qualifier", "", "mdi:flash-alert", None],
    "stressDuration": ["Stress Duration", "minutes", "mdi:flash-alert", None],
    "restStressDuration": ["Rest Stress Duration", "minutes", "mdi:flash-alert", None],
    "activityStressDuration": [
        "Activity Stress Duration",
        "minutes",
        "mdi:flash-alert",
        None,
    ],
    "uncategorizedStressDuration": [
        "Uncat. Stress Duration",
        "minutes",
        "mdi:flash-alert",
        None,
    ],
    "totalStressDuration": [
        "Total Stress Duration",
        "minutes",
        "mdi:flash-alert",
        None,
    ],
    "lowStressDuration": ["Low Stress Duration", "minutes", "mdi:flash-alert", None],
    "mediumStressDuration": [
        "Medium Stress Duration",
        "minutes",
        "mdi:flash-alert",
        None,
    ],
    "highStressDuration": ["High Stress Duration", "minutes", "mdi:flash-alert", None],
    "stressPercentage": ["Stress Percentage", "%", "mdi:flash-alert", None],
    "restStressPercentage": ["Rest Stress Percentage", "%", "mdi:flash-alert", None],
    "activityStressPercentage": [
        "Activity Stress Percentage",
        "%",
        "mdi:flash-alert",
        None,
    ],
    "uncategorizedStressPercentage": [
        "Uncat. Stress Percentage",
        "%",
        "mdi:flash-alert",
        None,
    ],
    "lowStressPercentage": ["Low Stress Percentage", "%", "mdi:flash-alert", None],
    "mediumStressPercentage": [
        "Medium Stress Percentage",
        "%",
        "mdi:flash-alert",
        None,
    ],
    "highStressPercentage": ["High Stress Percentage", "%", "mdi:flash-alert", None],
    "moderateIntensityMinutes": [
        "Moderate Intensity",
        "minutes",
        "mdi:flash-alert",
        None,
    ],
    "vigorousIntensityMinutes": ["Vigorous Intensity", "minutes", "mdi:run-fast", None],
    "intensityMinutesGoal": ["Intensity Goal", "minutes", "mdi:run-fast", None],
    "bodyBatteryChargedValue": [
        "Body Battery Charged",
        "%",
        "mdi:battery-charging-100",
        None,
    ],
    "bodyBatteryDrainedValue": [
        "Body Battery Drained",
        "%",
        "mdi:battery-alert-variant-outline",
        None,
    ],
    "bodyBatteryHighestValue": ["Body Battery Highest", "%", "mdi:battery-heart", None],
    "bodyBatteryLowestValue": [
        "Body Battery Lowest",
        "%",
        "mdi:battery-heart-outline",
        None,
    ],
    "bodyBatteryMostRecentValue": [
        "Body Battery Most Recent",
        "%",
        "mdi:battery-positive",
        None,
    ],
    "averageSpo2": ["Average SPO2", "%", "mdi:diabetes", None],
    "lowestSpo2": ["Lowest SPO2", "%", "mdi:diabetes", None],
    "latestSpo2": ["Latest SPO2", "%", "mdi:diabetes", None],
    "latestSpo2ReadingTimeLocal": [
        "Latest SPO2 Time",
        "",
        "mdi:diabetes",
        DEVICE_CLASS_TIMESTAMP,
    ],
    "averageMonitoringEnvironmentAltitude": [
        "Average Altitude",
        "%",
        "mdi:image-filter-hdr",
        None,
    ],
    "highestRespirationValue": [
        "Highest Respiration",
        "brpm",
        "mdi:progress-clock",
        None,
    ],
    "lowestRespirationValue": [
        "Lowest Respiration",
        "brpm",
        "mdi:progress-clock",
        None,
    ],
    "latestRespirationValue": [
        "Latest Respiration",
        "brpm",
        "mdi:progress-clock",
        None,
    ],
    "latestRespirationTimeGMT": [
        "Latest Respiration Update",
        "",
        "mdi:progress-clock",
        DEVICE_CLASS_TIMESTAMP,
    ],
}
