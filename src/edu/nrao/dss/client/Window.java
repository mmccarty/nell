package edu.nrao.dss.client;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import com.google.gwt.i18n.client.DateTimeFormat;
import com.google.gwt.json.client.JSONArray;
import com.google.gwt.json.client.JSONObject;
import com.google.gwt.widgetideas.graphics.client.Color;

@SuppressWarnings("unchecked")
class Window implements Comparable {
    private static final DateTimeFormat DATE_FORMAT = DateTimeFormat.getFormat("yyyy-MM-dd HH:mm:ss");

    public static Window parseJSON(Session session, JSONObject json) {
        int id = (int) json.get("id").isNumber().doubleValue();
        try {
        	int duration = (int) json.get("duration").isNumber().doubleValue();
            String start_time = json.get("start_time").isString().stringValue();
            List<String> receivers = parseReceivers(json.get("receiver").isArray());
            
            Window window = new Window(id, session, DATE_FORMAT.parse(start_time), duration, receivers);
            
            List<Interval> intervals = Interval.parseIntervals(window, json.get("opportunities").isArray());
            window.setIntervals(intervals);
            return window;
        } catch (NullPointerException e) {
        	return null;
        }
    }
    
    public static List<String> parseReceivers(JSONArray json) {
        ArrayList<String> receivers = new ArrayList<String>();
        for (int i = 0; i < json.size(); ++i) {
            JSONArray arr = json.get(i).isArray();
            for (int j = 0; j < arr.size(); ++j) {
                String rcvr = arr.get(j).isString().stringValue();
                receivers.add(rcvr);
            }
        }
        return receivers;
    }

    public Window(int id, Session session, Date startTime, int duration, List<String> receivers) {
        this.id        = id;
        this.session   = session;
        this.startTime = startTime;
        this.duration  = duration;
        this.receivers = receivers;
    }

    public String getReceivers() {
        StringBuilder sb = new StringBuilder();
        for (String s : receivers) {
            if (sb.length() > 0) {
                sb.append(",");
            }
            sb.append(s);
        }
        return sb.toString();
    }

    public boolean contains(int day, int hour) {
        int startDay  = getStartDay();
        int startHour = getStartHour() % 24;
        int numDays   = getNumDays();
        int numHours  = getNumHours();

        if (startHour + numHours > 24) {
            return (startDay <= day && day < startDay + numDays && startHour <= hour && hour < 24) ||
                   (startDay+1 <= day && day < startDay + numDays + 1 && 0 <= hour && hour < startHour + numHours - 24);
        }
        return startDay <= day && day < startDay + numDays && startHour <= hour && hour < startHour + numHours;
    }

    public void draw(Calendar grid) {
        int startDay  = getStartDay();
        int startHour = getStartHour() % 24;
        int numDays   = getNumDays();
        int numHours  = getNumHours();

        grid.setFillStyle(getColor());
        grid.fillRect(startDay, startHour, numDays, numHours);
        if (session.getType().equals("fixed")) { //if (numDays == 1) {
            grid.setStrokeStyle(new Color(0, 0, 0, getAlpha()));
            grid.setLineWidth(4);
            grid.strokeRect(startDay, startHour, 1, numHours);
        }
    }

    /** Return the number of opportunities. */
    public int getNumIntervals() {
        return intervals.size();
    }

    /** Return a list of opportunities. */
    public List<Interval> getIntervals() {
        return intervals;
    }

    /** Record the opportunities available to a given fixed or windowed session. */
    public void setIntervals(List<Interval> intervals) {
        this.intervals = new ArrayList<Interval>();

        // We're not prepared to deal with anything beyond the current trimester.
        for (Interval interval : intervals) {
            if (0 <= interval.getStartDay() && interval.getStartDay() < 120) {
                this.intervals.add(interval);
            }
        }
    }

    public int compareTo(Object other) {
        Window rhs = (Window) other;

        // Note that shorter windows sort *after* longer windows.  This is so that
        // shorter sessions get drawn on top of longer ones in the UI.
        if (getStartHour() <  rhs.getStartHour())                                       { return -1; }
        if (getStartHour() == rhs.getStartHour() && getNumHours() >  rhs.getNumHours()) { return -1; }
        if (getStartHour() == rhs.getStartHour() && getNumHours() == rhs.getNumHours()) { return  0; }
        return +1;
    }

    public Session getSession() {
    	return session;
    }
    
    /** A window begins on the day of its first opportunity. */
    public int getStartDay() {
        return intervals.get(0).getStartDay();
    }
    
    private int getNumDays() {
        int startDay = getStartDay();
        int endDay   = intervals.get(intervals.size()-1).getStartDay();
        return endDay - startDay + 1;
    }

    public int getStartHour() {
        return intervals.get(0).getStartHour();
    }

    public int getNumHours() {
        return intervals.get(0).getNumHours();
    }

    public void setStartDay(int day) {
        int deltaDays = day - getStartDay();
        for (Interval interval : intervals) {
            interval.setStartDay(interval.getStartDay() + deltaDays);
        }
        
        long date = startTime.getTime() + (long) deltaDays * (long) 86400 * (long) 1000;
        startTime = new Date(date);
        JSONRequest.post("/sessions/windows/"+id,
                new String[] {"_method", "start_time", "duration"},
                new String[] {"put", DATE_FORMAT.format(startTime), ""+duration},
                null);
    }
    
    public Date getStartTime() {
    	return startTime;
    }
    
    public int getDuration() {
    	return duration;
    }

    public Color getColor() {
        return new Color(red, green, blue, alpha);
    }

    public float getAlpha() {
        return alpha;
    }

    public void setRGB(int red, int green, int blue) {
        this.red   = red;
        this.green = green;
        this.blue  = blue;
    }

    public void setAlpha(float alpha) {
        this.alpha = alpha;
    }

    private int            id;
    private Session        session;
    private Date           startTime;
    private int            duration;
    private List<Interval> intervals;
    private List<String>   receivers;

    private int   red   = 0;
    private int   green = 0;
    private int   blue  = 0;
    private float alpha = 1.0f;
}
