package edu.nrao.dss.client;

import java.util.ArrayList;
import java.util.List;

import com.google.gwt.json.client.JSONArray;
import com.google.gwt.json.client.JSONObject;

/** A simplified representation of sessions designed for use in the overview calendar. */
class Session {
    public static void allocateColors(List<Session> sessions) {
        int c = 0;
        for (Session s : sessions) {
            if (s.isMaintenance()) {
                s.setRGB(0, 0, 0);
                continue;
            }
            s.setRGB(COLORS[c++ % COLORS.length]);
        }
    }

    private static final int[][] COLORS = {
        {0xFF, 0x00, 0x00}, {0x00, 0xFF, 0x00}, {0x00, 0x00, 0xFF}, {0x00, 0xFF, 0xFF},
        {0xFF, 0x00, 0xFF}, {0xFF, 0xFF, 0x00}, {0xFF, 0x77, 0x00}, {0x77, 0xFF, 0x00},
        {0x00, 0xFF, 0x77}, {0x00, 0x77, 0xFF}, {0x77, 0x00, 0xFF}, {0xFF, 0x00, 0x77},
        {0x00, 0x00, 0xFF}, {0x00, 0x66, 0xFF}, {0x00, 0xCC, 0x00}, {0x66, 0x66, 0x00},
        {0x99, 0x00, 0x00}, {0x99, 0x00, 0xFF}, {0xCC, 0x33, 0xFF}, {0xCC, 0x66, 0x00},
        {0xCC, 0xCC, 0xFF}, {0xCC, 0x99, 0x99}, {0xFF, 0xCC, 0x33}, {0xFF, 0xFF, 0x00},
        {0xFF, 0x99, 0x33}
    };

    /** Parse the list of sessions and opportunities generated by the server. */
    public static Session parseJSON(JSONObject json) {
        return parseJSON(json, false);
    }

    public static Session parseJSON(JSONObject json, boolean deep) {
    	JSONObject session = json.get("session").isObject();

    	Session sess    = new Session((int)session.get("id").isNumber().doubleValue());
    	sess.name       = session.get("name").isString().stringValue();
    	sess.receiver   = session.get("receiver").isString().stringValue();
    	sess.frequency  = "" + session.get("freq").isNumber().doubleValue();
    	sess.horizontal = "" + session.get("source_h").isNumber().doubleValue();
    	sess.science    = session.get("science").isString().stringValue();

    	if (deep) {
    	    sess.loadWindows();
    	}

    	return sess;
    }

    public void loadWindows() {
        JSONRequest.get("/sessions/"+id+"/windows", new JSONCallbackAdapter() {
            @Override
            public void onSuccess(JSONObject json) {
                windows = new ArrayList<Window>();
                JSONArray ws = json.get("windows").isArray();
                for (int i = 0; i < ws.size(); ++i) {
                    windows.add(Window.parseJSON(ws.get(i).isObject()));
                }
            }
        });
    }

    public Session(int id) {
        this.id = id;
    }

    public int getId() {
    	return id;
    }

    public boolean isMaintenance() {
        return name == "Maintenance";
    }

    public List<Window> getWindows() {
        return windows;
    }

    public String getName() {
    	return name;
    }

    public String getReceivers() {
    	return receiver;
    }

    public String getFrequency() {
    	return frequency;
    }

    public String getHorizontal() {
    	return horizontal;
    }

    public String getScience() {
    	return science;
    }

    public void setRGB(int[] rgb) {
        setRGB(rgb[0], rgb[1], rgb[2]);
    }
    
    public void setRGB(int r, int g, int b) {
        for (Window w : windows) {
            w.setRGB(r, g, b);
        }
    }

    private int    id         =  0;
    private String name       = "";
    private String receiver   = "";
    private String frequency  = "";
    private String horizontal = "";
    private String science    = "";

    private List<Window> windows;
}
