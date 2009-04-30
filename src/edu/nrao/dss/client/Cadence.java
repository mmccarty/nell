package edu.nrao.dss.client;

import java.util.Date;

import com.google.gwt.core.client.GWT;
import com.google.gwt.i18n.client.DateTimeFormat;
import com.google.gwt.json.client.JSONObject;
import com.google.gwt.json.client.JSONString;
import com.google.gwt.json.client.JSONValue;

public class Cadence {
	
	public Cadence(int s_id){
		session_id = s_id;
	}
	
	/** Parse the list of sessions and opportunities generated by the server. */
    public static Cadence parseJSON(JSONObject json) {
    	if (!json.containsKey("session_id")) {
    		return null;
    	}
    	Cadence cad    = new Cadence((int) json.get("session_id").isNumber().doubleValue());
    	cad.startDate  = JSONObjectToDate(json, "start_date");
    	cad.endDate    = JSONObjectToDate(json, "end_date");
    	JSONValue repeats = safeGet(json, "repeats");
    	if (repeats != null){
    		cad.repeats    = (int) repeats.isNumber().doubleValue();
    	}
    	JSONValue intervals = safeGet(json, "intervals");
    	if (intervals != null){
    		cad.intervals    = intervals.isString().stringValue();
    	}
    	JSONValue fullSize = safeGet(json, "full_size");
    	if (fullSize != null){
    		cad.fullSize    = fullSize.isString().stringValue();
    	}
    	return cad;
    }
    
    private static JSONValue safeGet(JSONObject json, String key){
    	try{
    		return json.get(key);
    	} catch (NullPointerException e){
    		return null;
    	}
    }
    
    private static Date JSONObjectToDate(JSONObject json, String key){
    	try {
    		JSONString str = json.get(key).isString();
    		DateTimeFormat fmt = DateTimeFormat.getFormat("MM/dd/yyyy");
    		return fmt.parse(str.stringValue());
    	} catch (NullPointerException e){
    		return null;
    	}
    }
    
    public Date getStartDate(){
    	return startDate;
    }
    
    public Date getEndDate(){
    	return endDate;
    }
    
    public int getRepeats(){
    	return repeats;
    }
    
    public String getIntervals(){
    	return intervals;
    }
    
    public String getFullSize(){
    	return fullSize;
    }
    
    private int session_id   = 0;
    private Date startDate   = new Date();
    private Date endDate     = new Date();
    private int repeats      = 0;
    private String intervals = new String();
    private String fullSize  = new String();
       
}
