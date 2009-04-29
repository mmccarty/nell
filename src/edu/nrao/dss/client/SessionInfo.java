package edu.nrao.dss.client;

import com.extjs.gxt.ui.client.Style.Orientation;
import com.extjs.gxt.ui.client.util.Margins;
import com.extjs.gxt.ui.client.widget.LayoutContainer;
import com.extjs.gxt.ui.client.widget.layout.RowData;
import com.extjs.gxt.ui.client.widget.layout.RowLayout;

/** Display session and cadence details on the overview calendar page. */
class SessionInfo extends LayoutContainer {
    public SessionInfo() {
        initLayout();
    }

    private void initLayout() {
        setLayout(new RowLayout(Orientation.HORIZONTAL));

        add(details, new RowData(0.25, 1.0, new Margins(10)));
        add(cadence, new RowData(0.25, 1.0, new Margins(10)));
    }

    private final SessionDetails details = new SessionDetails();
    private final CadenceDetails cadence = new CadenceDetails();
}
