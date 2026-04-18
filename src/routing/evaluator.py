from typing import Dict

class WorthItEvaluator:
    # 1 cigarette is roughly equivalent to inhaling 22 ug of PM2.5 in a day
    CIG_PM25_UG = 22.0

    def __init__(self, threshold_ug: float = 2.0, tolerance_time: float = 10.0):
        """
        threshold_ug: Minimum PM2.5 micrograms saving required to be "worth it".
        tolerance_time: Maximum extra minutes allowed to be "worth it".
        """
        self.threshold_ug = threshold_ug
        self.tolerance_time = tolerance_time

    def evaluate(self, fastest_route: Dict, quality_route: Dict) -> Dict:
        """
        Evaluates if the detour for better air quality is worth taking.
        """
        time_penalty = quality_route.get('time_min', 0) - fastest_route.get('time_min', 0)
        
        # Default to old exposure check if pm25_inhaled is missing
        if 'pm25_inhaled_ug' in fastest_route and 'pm25_inhaled_ug' in quality_route:
            f_ug = fastest_route['pm25_inhaled_ug']
            q_ug = quality_route['pm25_inhaled_ug']
            saving_value = f_ug - q_ug
            is_pm25 = True
        else:
            saving_value = fastest_route.get('exposure_index', 0) - quality_route.get('exposure_index', 0)
            is_pm25 = False
        
        # Evaluate threshold logic - we use self.threshold_ug for both to keep simple
        is_worth_it = (saving_value >= self.threshold_ug) and (time_penalty <= self.tolerance_time)
        
        reason = ""
        cigs_saved = saving_value / self.CIG_PM25_UG if is_pm25 else 0.0
        
        if is_worth_it:
            if is_pm25 and cigs_saved >= 0.05:
                reason = (f"Taking this route saves you from inhaling the equivalent of "
                          f"{cigs_saved:.1f} cigarettes worth of smog.")
            else:
                unit = "ug of PM2.5" if is_pm25 else "AQI-min"
                reason = (f"Taking the air-quality route saves {saving_value:.1f} {unit} "
                          f"at a cost of {time_penalty:.1f} min extra travel. Recommended.")
        elif saving_value < self.threshold_ug:
            reason = "The air quality improvement is negligible on this route."
        elif time_penalty > self.tolerance_time:
            reason = f"The time penalty ({time_penalty:.1f} min) is too high for the exposure savings."
            
        return {
            "is_worth_it": is_worth_it,
            "saving_value": saving_value,
            "cigs_saved": cigs_saved,
            "time_penalty": time_penalty,
            "reason": reason
        }

if __name__ == "__main__":
    evaluator = WorthItEvaluator()
    # Mock data
    f_route = {"time_min": 10.0, "pm25_inhaled_ug": 50.0}
    q_route = {"time_min": 14.0, "pm25_inhaled_ug": 15.0} # Saved 35 ug -> ~1.5 cigs
    
    result = evaluator.evaluate(f_route, q_route)
    print(result['reason'])
