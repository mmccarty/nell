Ext.define('PHT.view.plot.Window', {
    extend: 'Ext.window.Window',
    alias: 'widget.plotwindow',
    autoScroll: true,
    width: '90%',
    height: '90%',
    //layout: 'border',
    constrainHeader: true,
    title: 'Plots',

    maximizable: true,
    autoshow: true,

    items: [{
        xtype : 'lstpressureplot'
    }],


    initComponent: function() {    
        this.dockedItems = [{
            xtype: 'toolbar',
            items: [
                {
                    text: 'Update',
                    action: 'update',
                },
            ]
        }];
        this.callParent(arguments);
    },
});


