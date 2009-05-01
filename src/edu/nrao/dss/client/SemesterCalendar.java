package edu.nrao.dss.client;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.extjs.gxt.ui.client.Style.Orientation;
import com.extjs.gxt.ui.client.Style.Scroll;
import com.extjs.gxt.ui.client.widget.LayoutContainer;
import com.extjs.gxt.ui.client.widget.Text;
import com.extjs.gxt.ui.client.widget.layout.CenterLayout;
import com.extjs.gxt.ui.client.widget.layout.RowData;
import com.extjs.gxt.ui.client.widget.layout.RowLayout;
import com.google.gwt.core.client.GWT;
import com.google.gwt.json.client.JSONArray;
import com.google.gwt.json.client.JSONObject;
import com.google.gwt.user.client.Timer;
import com.google.gwt.user.client.ui.MouseListenerAdapter;
import com.google.gwt.user.client.ui.RootPanel;
import com.google.gwt.user.client.ui.Widget;
import com.google.gwt.widgetideas.graphics.client.GWTCanvas;

class SemesterCalendar extends LayoutContainer implements CanvasClient {
    public SemesterCalendar() {
        initLayout();
    }

    private void initLayout() {
        setLayout(new RowLayout(Orientation.VERTICAL));
        setScrollMode(Scroll.AUTO);

        add(top, new RowData(-1.0, 1.5 * Calendar.HEIGHT));
        top.setLayout(new CenterLayout());
        top.add(calendar);

        add(info, new RowData(-1.0, 300));
        addListeners();

        Timer timer = new Timer() {
            public void run() {
                if (++blinkCount % 10 == 0) {
                    blinkOn = ! blinkOn;
                }
                draw(blinkOn);
            }
            private int     blinkCount = 0;
            private boolean blinkOn    = true;
        };
        if (animated) {
            timer.scheduleRepeating(1000 / 10);
        }
        
        for (int i = 0; i < 120; ++i) {
            Text text = new Text("");
            top.add(text);
            text.setStyleAttribute("display", "inline");
            text.setWidth(0);
            pool.add(text);
        }

        draw(true);
    }

    public void load() {
        JSONRequest.get("/sessions/selected", new JSONCallbackAdapter() {
            public void onSuccess(JSONObject json){
                HashMap<String, Integer> selected = new HashMap<String, Integer>();
                JSONArray sessions = json.get("sessions").isArray();
                for (int i = 0; i < sessions.size(); ++i){
                    JSONObject s = sessions.get(i).isObject();
                    String name = s.get("name").isString().stringValue();
                    int value = (int) s.get("id").isNumber().doubleValue();
                    selected.put(name, value);
                }
                loadData(selected);
            }
        });
    }
    
    public void reload() {
        loading  = new ArrayList<Integer>();
        for (Session s : sessions) {
            loading.add(s.getId());
        }
        sessions = new ArrayList<Session>();
        loadNext();
    }

    /** Fetch the calendar data from the server. */
    private void loadData(Map<String, Integer> selected) {
        info.loadSessions(selected);

        loading  = new ArrayList<Integer>(selected.values());
        sessions = new ArrayList<Session>();
        loadNext();
    }

    private void loadNext() {
        if (loading.size() == 0) {
            // Kludgy delay to allow time to load windows and opportunities.
            Timer timer = new Timer() {
                public void run() {
                    Session.allocateColors(sessions);

                    windows = new ArrayList<Window>();
                    for (Session s : sessions) {
                        for (Window w : s.getWindows()) {
                            if (w.getNumIntervals() > 0) {
                                windows.add(w);
                            }
                        }
                    }

                    sortWindows();
                    draw(false);
                }
            };
            timer.schedule(1000);
            return;
        }

        int id = loading.get(0);
        loading.remove(0);

        JSONRequest.get("/sessions/"+id, new JSONCallbackAdapter() {
            @Override
            public void onSuccess(JSONObject json) {
                Session s = Session.parseJSON(json, true);
                sessions.add(s);
                loadNext();
            }
        });
    }

    private void addListeners() {
        calendar.addClient(this);

        calendar.addMouseListener(new MouseListenerAdapter() {
            public void onMouseDown(Widget sender, int x, int y) {
                dragTarget = hitTestWindow(x, y);
                if (dragTarget != null) {
                    dragStartX   = x;
                    dragStartDay = calendar.pixelsToDays(x);
                }
            }

            public void onMouseUp(Widget sender, int x, int y) {
                if (dragTarget != null) {
                    int deltaDays = calendar.pixelsToDays(x) - dragStartDay;
                    dragTarget.setStartDay(dragTarget.getStartDay() + deltaDays);
                    sortWindows();
                }

                dragTarget = null;
            }

            public void onMouseMove(Widget sender, int x, int y) {
                mouseX = x;
                mouseY = y;

                current = dragTarget;
                if (current == null) {
                    current = findCurrentWindow();
                }
                details.showWindowDetails(current);

                if (! animated) {
                    draw(true);
                }
            }
        });
    }
    
    public WindowDetails getWindowDetails() {
        details = new WindowDetails();
        return details;
    }

    private void draw(boolean showConflicts) {
        this.showConflicts = showConflicts;
        calendar.draw();
        this.showConflicts = false;
        
        drawLabels();
    }

    private void drawLabels() {
        for (int i = 0; i < labels.size(); ++i) {
            int x = dayToX(offsets.get(i));
            labels.get(i).setPagePosition(x, 80);
        }
    }
    
    private int dayToX(int day) {
        int center = top.getWidth() / 2;
        return center + (day - 60) * 12;
    }

    private ArrayList<Text>    labels  = new ArrayList<Text>();
    private ArrayList<Integer> offsets = new ArrayList<Integer>();
    private ArrayList<Text>    pool    = new ArrayList<Text>();
    
    private void displayReceivers() {
        for (Text text : labels) {
            text.setText("");
            text.setPagePosition(0, 0);
        }
        labels  = new ArrayList<Text>();
        offsets = new ArrayList<Integer>();
        
        for (int i = 0; i < windows.size(); ++i) {
            Window w = windows.get(i);
            Text text = pool.get(i);
            text.setText(w.getReceivers());
            labels.add(text);
            offsets.add(w.getStartDay());
        }

        drawLabels();
    }

    public void onPaint(GWTCanvas canvas) {
        for (Window a : windows) {
            if (! showConflicts && problems != null && problems.contains(a)) { continue; }
            if (a != dragTarget && a != current) {
                a.setAlpha(0.6f);
                a.draw(calendar);
            }
        }

        if (dragTarget != null) {
            dragTarget.setAlpha(1.0f);
            calendar.saveContext();
            calendar.translate(mouseX - dragStartX, 0);
            dragTarget.draw(calendar);
            calendar.restoreContext();
        } else if (current != null) {
            current.setAlpha(1.0f);
            current.draw(calendar);
        }
    }

    private Window findCurrentWindow() {
        return hitTestWindow(mouseX, mouseY);
    }

    private Window hitTestWindow(int x, int y) {
        int day  = calendar.positionToDay(x);
        int hour = calendar.positionToHour(y);

        Window result = null;
        for (Window a : windows) {
            if (a.contains(day, hour)) {
                result = a;
            }
        }

        return result;
    }

    /** Sort sessions chronologically, so they can be drawn such the everything is visible. */
    @SuppressWarnings("unchecked")
    private void sortWindows() {
        Collections.sort(windows);
        problems = sudoku.findProblem(windows);
        
        displayReceivers();
    }

    private final LayoutContainer top  = new LayoutContainer();
    private final Calendar    calendar = new Calendar();
    private final SessionInfo info     = new SessionInfo(this);
    private final Sudoku      sudoku   = new Sudoku();

    private WindowDetails  details;

    /** Set to true to enable annoying blinking effects. */
    private final boolean  animated = true;

    private List<Session> sessions = new ArrayList<Session>();
    private List<Window>  windows  = new ArrayList<Window>();
    private List<Window>  problems;
    private Window        dragTarget;
    private Window        current;

    private List<Integer> loading  = new ArrayList<Integer>();

    private int dragStartX;
    private int dragStartDay;
    private int mouseX;
    private int mouseY;

    private boolean showConflicts = false;
}
