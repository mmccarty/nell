// Here we use a simple local store, since the allowed state
// on the server side is just a NullBooleanField
var allowedStates = Ext.create('Ext.data.Store', {
    fields: ['type'],
    data: [{type: 'allowed'},
           {type: 'not allowed'},
           {type: 'unknown'}
          ],
});


Ext.define('PHT.view.source.Edit', {
    extend: 'Ext.window.Window',
    alias : 'widget.sourceedit',

    title : 'Edit Source',
    layout: 'fit',
    autoShow: true,
    plain: true,
    //constrain: true,

    initComponent: function() {
        this.items = [
            {
                xtype: 'form',
                items: [
                    {
                        xtype: 'textfield',
                        name : 'target_name',
                        fieldLabel: 'Name',
                        allowBlank: false,
                        labelStyle: 'font-weight:bold',
                    },{
                        xtype: 'combo',
                        name: 'pcode',
                        fieldLabel: 'PCODE',
                        store : 'ProposalCodes',
                        queryMode: 'local',
                        displayField: 'pcode',
                        valueField: 'pcode',
                        allowBlank: false,
                        labelStyle: 'font-weight:bold',
                    },{
                        xtype: 'textfield',
                        name : 'coordinate_system',
                        fieldLabel: 'Coordinate System',
                    },{
                        xtype: 'textfield',
                        name : 'ra',
                        fieldLabel: 'RA (Hrs)',
                        vtype: 'hourField',
                    },{
                        xtype: 'textfield',
                        name : 'dec',
                        fieldLabel: 'Dec (Deg)',
                        vtype: 'degreeField',
                    },{
                        xtype: 'textfield',
                        name : 'ra_range',
                        fieldLabel: 'RA Range (Hrs)',
                        vtype: 'hourField',
                    },{
                        xtype: 'textfield',
                        name : 'dec_range',
                        fieldLabel: 'Dec Range (Deg)',
                        vtype: 'degreeField',
                    },{
                        xtype: 'textfield',
                        name : 'velocity_units',
                        fieldLabel: 'Velocity Units',
                    },{
                        xtype: 'textfield',
                        name : 'velocity_redshit',
                        fieldLabel: 'Velocity Redshift',
                    },{
                        xtype: 'textfield',
                        name : 'convention',
                        fieldLabel: 'Convention',
                    },{
                        xtype: 'textfield',
                        name : 'reference_frame',
                        fieldLabel: 'Reference Frame',
                    },{
                        xtype: 'combo',
                        fieldLabel: 'Allowed',
                        name: 'allowed',
                        store : allowedStates,
                        queryMode: 'local',
                        displayField: 'type',
                        valueField: 'type',
                        allowBlank: false,
                        labelStyle: 'font-weight:bold',
                    },{
                        xtype: 'checkboxfield',
                        fieldLabel: 'Observed',
                        boxLabel: 'Observed',
                        name: 'observed',
                        uncheckedValue: 'false',
                        inputValue: 'true'
                    },{
                        xtype: 'fieldset',
                        title: 'Original PST Values',
                        collapsible: true,
                        collapsed: true,
                        items: [{
                            xtype: 'textfield',
                            name : 'pst_ra',
                            fieldLabel: 'PST RA',
                            readOnly: true,
                        },{
                            xtype: 'textfield',
                            name : 'pst_ra_range',
                            fieldLabel: 'PST RA Range',
                            readOnly: true,
                        },{
                            xtype: 'textfield',
                            name : 'pst_dec',
                            fieldLabel: 'PST Dec',
                            readOnly: true,
                        },{
                            xtype: 'textfield',
                            name : 'pst_dec_range',
                            fieldLabel: 'PST Dec Range',
                            readOnly: true,
                        }]
                    }
                ]
            },

        ];

        this.buttons = [
            {
                text: 'Save',
                action: 'save',
                // does this not work because we aren't 'inside' the form?
                formBind: true,
            },
            {
                text: 'Close',
                scope: this,
                handler: this.hide,
            },
        ];

        this.callParent(arguments);
    },

});
