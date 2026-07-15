"""
Bloomberg API Test Script
Fetches PX_LAST for JPBYARZS Index
"""
import blpapi


def fetch_bloomberg_data(securities, fields):
    """
    Fetch reference data from Bloomberg
    
    Args:
        securities: List of securities (e.g., ["JPBYARZS Index"])
        fields: List of fields (e.g., ["PX_LAST"])
    """
    # Start a session
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    
    if not session.start():
        print("❌ Failed to start session. Is Bloomberg Terminal running?")
        return None
    
    print("✓ Session started successfully")
    
    if not session.openService("//blp/refdata"):
        print("❌ Failed to open //blp/refdata service")
        session.stop()
        return None
    
    print("✓ Opened reference data service")
    
    # Get the service
    refdata_service = session.getService("//blp/refdata")
    
    # Create request
    request = refdata_service.createRequest("ReferenceDataRequest")
    
    # Add securities and fields
    for security in securities:
        request.append("securities", security)
    
    for field in fields:
        request.append("fields", field)
    
    print(f"\n📡 Requesting data for: {securities}")
    print(f"   Fields: {fields}\n")
    
    # Send request
    session.sendRequest(request)
    
    results = {}
    
    # Process response
    try:
        while True:
            event = session.nextEvent(500)
            
            if event.eventType() == blpapi.Event.RESPONSE or \
               event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                
                for msg in event:
                    security_data = msg.getElement("securityData")
                    
                    for i in range(security_data.numValues()):
                        field_data = security_data.getValueAsElement(i)
                        security = field_data.getElementAsString("security")
                        
                        # Check for errors
                        if field_data.hasElement("securityError"):
                            error = field_data.getElement("securityError")
                            print(f"❌ {security}: Error - {error}")
                            continue
                        
                        field_data_element = field_data.getElement("fieldData")
                        
                        results[security] = {}
                        
                        for field in fields:
                            if field_data_element.hasElement(field):
                                value = field_data_element.getElement(field).getValue()
                                results[security][field] = value
                                print(f"✓ {security}: {field} = {value}")
                            else:
                                print(f"⚠ {security}: {field} not available")
                                results[security][field] = None
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
                
    finally:
        session.stop()
        print("\n✓ Session closed")
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("Bloomberg API Connection Test")
    print("=" * 60)
    
    # Test with JPBYARZS Index
    securities = ["JPBYARZS Index"]
    fields = ["PX_LAST"]
    
    try:
        results = fetch_bloomberg_data(securities, fields)
        
        if results:
            print("\n" + "=" * 60)
            print("Results Summary:")
            print("=" * 60)
            for security, data in results.items():
                print(f"\n{security}:")
                for field, value in data.items():
                    print(f"  {field}: {value}")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Bloomberg Terminal is running")
        print("  2. Check that blpapi is installed: pip show blpapi")
        print("  3. Verify Terminal API is enabled in WAPI<GO>")
