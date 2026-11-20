from datetime import date

from app.pricing import (
    FlightQuote,
    HotelQuote,
    TripPriceSearchRequest,
    recommend_trip_options,
)


def test_ranks_combined_flight_and_hotel_cost_not_flight_alone():
    request = TripPriceSearchRequest(
        destination="Japan",
        destination_country="Japan",
        origin_airport="SEA",
        flight_quotes=[
            FlightQuote(departure_date="2027-04-01", return_date="2027-04-10",
                        origin_airport="SEA", arrival_airport="HND",
                        return_departure_airport="NRT", arrival_country="Japan",
                        return_departure_country="Japan", price=500, currency="USD"),
            FlightQuote(departure_date="2027-04-12", return_date="2027-04-21",
                        origin_airport="SEA", arrival_airport="KIX",
                        return_departure_airport="KIX", arrival_country="Japan",
                        return_departure_country="Japan", price=650, currency="USD"),
        ],
        hotel_quotes=[
            HotelQuote(check_in="2027-04-01", check_out="2027-04-10",
                       name="Tokyo hotel", price=1000, currency="USD"),
            HotelQuote(check_in="2027-04-12", check_out="2027-04-21",
                       name="Japan hotel", price=500, currency="USD"),
        ],
    )
    result = recommend_trip_options(request)
    assert [option.total_price for option in result.recommendations] == [1150, 1500]
    assert result.recommendations[0].arrival_airport == "KIX"


def test_rejects_airports_outside_fixed_destination_country():
    request = TripPriceSearchRequest(
        destination="Japan",
        destination_country="Japan",
        origin_airport="SEA",
        flight_quotes=[
            FlightQuote(departure_date="2027-04-12", return_date="2027-04-21",
                        origin_airport="SEA", arrival_airport="ICN",
                        return_departure_airport="ICN", arrival_country="South Korea",
                        return_departure_country="South Korea", price=400, currency="USD"),
        ],
        hotel_quotes=[
            HotelQuote(check_in="2027-04-12", check_out="2027-04-21",
                       name="Hotel", price=500, currency="USD"),
        ],
    )
    result = recommend_trip_options(request)
    assert result.recommendations == []
    assert result.rejected_options == 1


def test_returns_booking_links_from_quote_sources():
    request = TripPriceSearchRequest(
        destination="Japan",
        destination_country="Japan",
        origin_airport="SEA",
        flight_quotes=[
            FlightQuote(departure_date="2027-04-12", return_date="2027-04-21",
                        origin_airport="SEA", arrival_airport="HND",
                        return_departure_airport="KIX", arrival_country="Japan",
                        return_departure_country="Japan", price=650, currency="USD",
                        booking_url="https://example.com/flight"),
        ],
        hotel_quotes=[
            HotelQuote(check_in="2027-04-12", check_out="2027-04-21",
                       name="Hotel", price=500, currency="USD",
                       booking_url="https://example.com/hotel"),
        ],
    )
    result = recommend_trip_options(request)
    assert result.recommendations[0].booking_links == {
        "flight": "https://example.com/flight",
        "hotel": "https://example.com/hotel",
    }
