"""Unit tests for utils.timing module."""

import pytest
from fibermorph.utils.timing import convert, timing


class TestConvert:
    """Tests for convert function."""
    
    def test_convert_seconds_only(self):
        """Test conversion of seconds only."""
        result = convert(30)
        assert result == "0h: 00m: 30s"
    
    def test_convert_minutes(self):
        """Test conversion of minutes."""
        result = convert(60)
        assert result == "0h: 01m: 00s"
    
    def test_convert_hours(self):
        """Test conversion of hours."""
        result = convert(3600)
        assert result == "1h: 00m: 00s"
    
    def test_convert_mixed(self):
        """Test conversion of mixed hours, minutes, and seconds."""
        result = convert(5400)
        assert result == "1h: 30m: 00s"
    
    def test_convert_complex(self):
        """Test conversion of complex time."""
        result = convert(3661)
        assert result == "1h: 01m: 01s"
    
    def test_convert_zero(self):
        """Test conversion of zero seconds."""
        result = convert(0)
        assert result == "0h: 00m: 00s"
    
    def test_convert_large_number(self):
        """Test conversion of large number of seconds."""
        result = convert(7325)
        assert result == "2h: 02m: 05s"


class TestTiming:
    """Tests for timing decorator."""
    
    def test_timing_decorator_simple(self):
        """Test timing decorator with simple function."""
        @timing
        def simple_function():
            return "test"
        
        result = simple_function()
        assert result == "test"
    
    def test_timing_decorator_with_args(self):
        """Test timing decorator with function that takes arguments."""
        @timing
        def add_function(a, b):
            return a + b
        
        result = add_function(2, 3)
        assert result == 5
    
    def test_timing_decorator_with_kwargs(self):
        """Test timing decorator with function that takes kwargs."""
        @timing
        def multiply_function(a, b=2):
            return a * b
        
        result = multiply_function(3, b=4)
        assert result == 12
    
    def test_timing_decorator_preserves_function_name(self):
        """Test that timing decorator preserves function name."""
        @timing
        def named_function():
            return None
        
        assert named_function.__name__ == "named_function"
