Ext.define('PHT.model.Session', {
    extend: 'Ext.data.Model',
    fields: ['id'
           , 'pst_session_id'
           , 'pcode'
           , 'name'
           , 'other_receiver'
           , 'other_backend'
           , 'sci_categories'
           , 'session_type'
           , 'session_type_code'
           , 'observing_type'
           , 'weather_type'
           , 'semester'
           , 'grade'
           , 'backends'
           , 'receivers'
           , 'receivers_granted'
           , 'constraint_field'
           , 'has_constraint_field'
           , 'comments'
           , 'has_comments'
           , 'scheduler_notes'
           , 'session_time_calculated'
           // allotment
           , 'repeats'
           , 'separation'
           , 'interval_time'
           , 'requested_time'
           , 'requested_total'
           , 'allocated_time'
           , 'allocated_repeats'
           , 'allocated_total'
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
           , 'solar_avoid'
           // flags
           , 'thermal_night'
           , 'rfi_night'
           , 'optical_night'
           , 'transit_flat'
           , 'guaranteed'
           // monitoring
           , 'inner_repeats'
           , 'inner_separation'
           , 'inner_interval'
           , 'start_date'
           , 'start_time'
           , 'window_size'
           , 'outer_window_size'
           , 'outer_repeats'
           , 'outer_separation'
           , 'outer_interval'
           , 'custom_sequence'
           // next semester
           , 'next_sem_complete'
           , 'next_sem_time'
           , 'next_sem_repeats'
           // session params
           , 'lst_ex'
           , 'lst_in'
           // raw pst values (readonly)
           , 'pst_min_lst'
           , 'pst_max_lst'
           , 'pst_elevation_min'
           // dss session (readonly)
           , 'dss_session'
           , 'dss_total_time'
           , 'dss_session_complete'
           , 'billed_time'
           , 'scheduled_time'
           , 'remaining_time'
           , 'last_date_scheduled'
           ], 
    proxy: {
        type: 'rest',
        url: '/pht/sessions',
        timeout: 300000,
        reader: {
            type: 'json',
            root: 'sessions',
            successProperty: 'success',
            totalProperty: 'total',
        }
    }
});
