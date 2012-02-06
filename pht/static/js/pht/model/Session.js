Ext.define('PHT.model.Session', {
    extend: 'Ext.data.Model',
    fields: ['id'
           , 'pst_session_id'
           , 'pcode'
           , 'name'
           , 'session_type'
           , 'weather_type'
           , 'semester'
           , 'grade'
           , 'backends'
           , 'receivers'
           , 'receivers_granted'
           , 'constraint_field'
           , 'comments'
           , 'scheduler_notes'
           , 'session_time_calculated'
           // allotment
           , 'repeats'
           , 'separation'
           , 'interval_time'
           , 'requested_time'
           , 'allocated_time'
           , 'semester_time'
           , 'period_time'
           , 'low_freq_time'
           , 'hi_freq_1_time'
           , 'hi_freq_2_time'
           // target
           , 'ra'
           , 'dec'
           , 'center_lst'
           , 'lst_width'
           , 'min_lst'
           , 'max_lst'
           , 'elevation_min'
           // flags
           , 'thermal_night'
           , 'rfi_night'
           , 'optical_night'
           , 'transit_flat'
           , 'guaranteed'
           // session params
           , 'lst_ex'
           , 'lst_in'
           // raw pst values (readonly)
           , 'pst_min_lst'
           , 'pst_max_lst'
           , 'pst_elevation_min'
           ], 
    proxy: {
        type: 'rest',
        url: 'sessions',
        reader: {
            type: 'json',
            root: 'sessions',
            successProperty: 'success'
        }
    }
});
