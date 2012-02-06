// TBFs: units, formats, validations


Ext.define('PHT.view.session.Form', {
    extend: 'Ext.form.Panel',
    alias:  'widget.sessionform',
    bodyStyle:'padding:5px',
    width: 600,
    fieldDefaults: {
        labelAlign: 'top',
        msgTarget: 'side'
    },
    defaults: {
        anchor: '90%',
        border: false
    },
    items: [{
        // First, all basic parameters, in two columns
        layout: 'column',
        border: false,
        items:[{
            // First Column
            columnWidth: 0.3333,
            border: false,
            layout: 'anchor',
            items: [{
                xtype: 'textfield',
                name: 'name',
                fieldLabel: 'Name',
                allowBlank: false,
                labelStyle: 'font-weight:bold',
            },{
                xtype: 'combo',
                name: 'pcode',
                fieldLabel: 'PCODE',
                store: 'ProposalCodes', // MVC baby!
                queryMode: 'local',
                displayField: 'pcode',
                valueField: 'pcode',
                forceSelection: true,
                allowBlank: false,
                labelStyle: 'font-weight:bold',
            },{
                xtype: 'combo',
                name: 'semester',
                fieldLabel: 'Semester',
                store: 'Semesters', // MVC baby!
                queryMode: 'local',
                displayField: 'semester',
                valueField: 'semester',
                forceSelection: true,
                allowBlank: false,
                labelStyle: 'font-weight:bold',
            },{    
                xtype: 'combo',
                name: 'session_type',
                fieldLabel: 'Session Type',
                store: 'SessionTypes', // MVC baby!
                queryMode: 'local',
                displayField: 'type',
                valueField: 'type',
                forceSelection: true,
                allowBlank: false,
                labelStyle: 'font-weight:bold',
            },{    
                xtype: 'combo',
                name: 'weather_type',
                fieldLabel: 'Weather Type',
                store: 'WeatherTypes', // MVC baby!
                queryMode: 'local',
                displayField: 'type',
                valueField: 'type',
                forceSelection: true,
                allowBlank: false,
                labelStyle: 'font-weight:bold',
            }],
           
        },{    
            // Second Column
            columnWidth: 0.333,
            border: false,
            layout: 'anchor',
            items: [{
                xtype: 'textfield',
                name: 'grade',
                fieldLabel: 'Grade',
            },{
                xtype: 'numberfield',
                fieldLabel: 'Requested Time (Hrs)',
                        name: 'requested_time',
            },{
                xtype: 'numberfield',
                fieldLabel: 'Allocated (Hrs)',
                name: 'allocated_time',
            },{
                xtype: 'numberfield',
                fieldLabel: 'Repeats',
                name: 'repeats'
            },{
                xtype: 'numberfield',
                fieldLabel: 'Period (Hrs)',
                name: 'period_time'
            }]    
        },{    
            // Thrids Column
            columnWidth: 0.333,
            border: false,
            layout: 'anchor',
            items: [{
                xtype: 'textfield',
                fieldLabel: 'RA (Hrs)',
                name: 'ra',
                vtype: 'hourField',
            },{
                xtype: 'textfield',
                fieldLabel: 'Dec (Deg)',
                name: 'dec',
                vtype: 'degreeField',
            },{
                xtype: 'textfield',
                fieldLabel: 'Min. LST (Hrs)',
                name: 'min_lst',
                vtype: 'hourField',
            },{
                xtype: 'textfield',
                fieldLabel: 'Max. LST (Hrs)',
                name: 'max_lst',
                vtype: 'hourField',
            },{
                xtype: 'textfield',
                fieldLabel: 'Center LST (Hrs)',
                name: 'center_lst',
                vtype: 'hourField',
            }]
        }],
        // Tabbed by subject
        },{
            xtype: 'tabpanel',
            title: 'Session Details',
            collapsible: true,
            collapsed: true,
            items: [{
                // Allotment Tab
                title: 'Allotment',
                layout: 'column',
                defaults:{bodyStyle:'padding:10px'},
                items: [{
                    // First Column
                    columnwidth: 0.333,
                    border: false,
                    items: [{ 
                        xtype: 'numberfield',
                        fieldLabel: 'Semester (Hrs)',
                        name: 'semester_time',
                    },{
                        xtype: 'numberfield',
                        fieldLabel: 'Interval',
                        name: 'interval_time'
                    }],
                },{
                    // Second Column
                    columnwidth:0.333,
                    border: false,
                    items: [{ 
                        xtype: 'textfield',
                        fieldLabel: 'Separation',
                        name: 'separation'
                    },{
                        xtype: 'numberfield',
                        fieldLabel: 'Low Freq (Hrs)',
                        name: 'low_freq_time'
                    }],
                },{
                    // Third Column
                    columnwidth:0.333,
                    border: false,
                    items: [{ 
                        xtype: 'numberfield',
                        fieldLabel: 'High Freq 1 (Hrs)',
                        name: 'hi_freq_1_time'
                    },{
                        xtype: 'numberfield',
                        fieldLabel: 'High Freq 2 (Hrs)',
                        name: 'hi_freq_2_time'
                    }],
                }],    
            },{
                // Target Tab
                title: 'Target',
                layout: 'column',
                defaults:{bodyStyle:'padding:10px'},
                items: [{
                    // First Column
                    columnwidth: 0.5,
                    border: false,
                    items: [{
                        fieldLabel: 'Horizon Limit',
                        name: 'elevation_min',
                        vtype: 'degreeField',
                        xtype: 'textfield',
                    },{
                        fieldLabel: 'LST Width (Hrs)',
                        name: 'LST Width',
                        vtype: 'hourField',
                        xtype: 'textfield',
                    }],    
                },{
                    // Second Column
                    columnwidth: 0.5,
                    border: false,
                    items: [{
                        xtype: 'textfield',
                        fieldLabel: 'LST Exclusion (Hrs)',
                        name: 'lst_ex',
                    },{
                        xtype: 'textfield',
                        fieldLabel: 'LST Inclusion (Hrs)',
                        name: 'lst_in',
                    }]    
                }]
            },{
                title: 'Flags',
                layout: 'column',
                defaults:{bodyStyle:'padding:10px'},
                items: [{
                    // First Column
                    columnwidth: 0.5,
                    border: false,
                    items: [{
                        xtype: 'checkboxfield',
                        name: 'thermal_night',
                        fieldLabel: 'Thermal Night',
                        uncheckedValue: 'false',
                        inputValue: 'true',
                        labelAlign: 'left',
                    },{
                        xtype: 'checkboxfield',
                        name: 'rfi_night',
                        fieldLabel: 'RFI Night',
                        uncheckedValue: 'false',
                        inputValue: 'true',
                        labelAlign: 'left',
                    },{
                        xtype: 'checkboxfield',
                        name: 'optical_night',
                        fieldLabel: 'Optical Night',
                        uncheckedValue: 'false',
                        inputValue: 'true',
                        labelAlign: 'left',
                    }]
                },{
                    // Second column
                    columnwidth: 0.5, 
                    border: false,
                    items: [{
                        xtype: 'checkboxfield',
                        name: 'transit_flat',
                        fieldLabel: 'Transit Flat',
                        uncheckedValue: 'false',
                        inputValue: 'true',
                        labelAlign: 'left',
                    },{
                        xtype: 'checkboxfield',
                        name: 'guaranteed',
                        fieldLabel: 'Guaranteed',
                        uncheckedValue: 'false',
                        inputValue: 'true',
                        labelAlign: 'left',
                    }]                
                }]    
            },{
                title: 'Notes',
                defaults:{bodyStyle:'padding:10px'},
                borders: false,
                items: [{
                    xtype: 'textarea',
                    name: 'scheduler_notes',
                    fieldLabel: 'Scheduler Notes',
                    width: 500,
                    height: 100,
                },{
                    xtype: 'textarea',
                    name: 'constraint_field',
                    fieldLabel: 'Constraint',
                    width: 500,
                    height: 100,
                },{
                    xtype: 'textarea',
                    name: 'comments',
                    fieldLabel: 'Comments',
                    width: 500,
                    height: 100,
                    
                }]
            },{
                title: 'Resources',
                items: [{
                    xtype: 'textfield',
                    name: 'backends',
                    fieldLabel: 'Backends Requested',
                    vtype: 'backendList',
                    labelAlign: 'left',
                    labelWidth: 150,
                    width: 500,
                },{    
                    xtype: 'textfield',
                    name: 'receivers',
                    fieldLabel: 'Receivers Requested',
                    vtype: 'receiverList',
                    labelAlign: 'left',
                    labelWidth: 150,
                    width: 500,
                },{    
                    xtype: 'textfield',
                    name: 'receivers_granted',
                    fieldLabel: 'Receivers Granted',
                    vtype: 'receiverList',
                    labelAlign: 'left',
                    labelWidth: 150,
                    width: 500,
                }]
            },{
                title: 'Misc',
                items: [{
                    xtype: 'checkboxfield',
                    name: 'session_time_calculated',
                    fieldLabel: 'Sess Time Calc',
                    uncheckedValue: 'false',
                    inputValue: 'true',
                    labelAlign: 'left',
                }]    
            },{
                title: 'Original PST Values',
                items: [{
                    xtype: 'textfield',
                    fieldLabel: 'PST Min LST',
                    name: 'pst_min_lst',
                    readOnly: true,
                },{
                    xtype: 'textfield',
                    fieldLabel: 'PST Max LST',
                    name: 'pst_max_lst',
                    readOnly: true,
                },{
                    xtype: 'textfield',
                    fieldLabel: 'PST Horizon Limit',
                    name: 'pst_elevation_min',
                    readOnly: true,
                }]
            }],
        },    
    ],
});             
    
