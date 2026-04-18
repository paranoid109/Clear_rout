import random
import time

class BaseAQISensor:
    def read_aqi(self) -> float:
        raise NotImplementedError

class MockAQISensor(BaseAQISensor):
    """
    Mock sensor for development. 
    Simulates MQ-135/SDS011 behavior by returning plausible AQI values.
    """
    def __init__(self, base_val=45, noise=5):
        self.base_val = base_val
        self.noise = noise

    def read_aqi(self) -> float:
        """Returns a simulated AQI reading with some random fluctuation."""
        fluctuation = random.uniform(-self.noise, self.noise)
        return max(0, self.base_val + fluctuation)

if __name__ == "__main__":
    sensor = MockAQISensor()
    print("Reading from mock sensor...")
    for _ in range(5):
        print(f"Reading: {sensor.read_aqi():.2f}")
        time.sleep(1)

