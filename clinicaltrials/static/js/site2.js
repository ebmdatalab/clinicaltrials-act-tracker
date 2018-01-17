function getQueryVariable(variable, coerceArray) {
  var query = window.location.search.substring(1);
  var vars = query.split('&');
  var vals = [];
  for (var i=0; i<vars.length; i++) {
    var pair = vars[i].split('=');
    if (pair[0] == variable) {
      vals.push(pair[1]);
    }
  }
  if (!coerceArray && vals.length == 1) {
    return vals[0];
  } else {
    return vals;
  }

}

function rankingTable() {
  var url = '/api/rankings/?limit=5000';
  url += '&date=' + latest_date;
  var params = getParams();
  $('#total__gte').val(params['min_total']);
  if (params['is_industry_sponsor']) {
    $('.sponsor_type[value="'+params['is_industry_sponsor']+'"]').prop('checked', true);
  }
  var table = $('#sponsor_table').DataTable( {
    'ajax': {
      'url': url,
      'dataSrc': 'results',
      'data': function(d) {
        return $.extend({}, d, {
          'total__gte': $('#total__gte').val(),
          'with_trials_due': $('.overdue_type:checked').val(),
          'sponsor__is_industry_sponsor': $('.sponsor_type:checked').val(),
        });
      },
    },
    'pageLength': 300,
    'serverSide': true,
    'columns': [
      {'data': 'rank'},
      {'data': 'sponsor',
       'render': function(data, type, full, meta) {
         return '<a href="/sponsor/'+full['sponsor_slug']+'">'+
           full['sponsor_name']+'</a>';
       },
      },
      {'data': 'total'},
      {'data': 'due'},
      {'data': 'reported'},
      {'data': 'percentage'},
    ],
  });
  $('#total__gte').on('input', function() {
    table.draw();
    params = getParams();
    params['min_total'] = $('#total__gte').val();
    window.history.pushState('min_total', '', '?' + $.param(params));
  });
  $('.sponsor_type').on('change', function() {
    table.draw();
    params = getParams();
    params['is_industry_sponsor'] = $('.sponsor_type:checked').val();
    window.history.pushState('industry_sponsor', '', '?' + $.param(params));
  });
  $('.overdue_type').on('change', function() {
    table.draw();
    params = getParams();
    params['with_trials_due'] = $('.with_trials_due:checked').val();
    window.history.pushState('with_trials_due', '', '?' + $.param(params));
  });
}

function getParams() {
  var is_industry_sponsor = getQueryVariable('is_industry_sponsor');
  var min_total = getQueryVariable('min_total');
  var q = getQueryVariable('q');
  var with_trials_due = getQueryVariable('with_trials_due');
  var params = {
    'is_industry_sponsor': is_industry_sponsor,
    'min_total': min_total,
    'with_trials_due': with_trials_due,
    'q': q,
  };
  return params;
}

function getTrialParams() {
  var status = getQueryVariable('status');
  var params = {
    'status': status,
  };
  return params;
}


// add to query string


function trialsTable(sponsor_slug) {
  if(typeof sponsor_slug !== 'undefined') {
    var url = '/api/trials/?limit=5000&sponsor=' + sponsor_slug;
  } else {
    var url = '/api/trials/?limit=5000';
  }
  statuses = getQueryVariable('status', true);
  console.log(statuses);
  if (statuses.length > 0) {
    $('.status_filter').prop('checked', false);
    $.each(statuses, function(i, d) {
      $('.status_filter[value="'+d+'"]').prop('checked', true);
    });
  }
  var table = $('#trials_table').DataTable( {
    'ajax': {
      'url': url,
      'dataSrc': 'results',
      'data': function(d) {
        return $.extend({}, d, {
          'status': $.map($('.status_filter:checked'), function(x) {return $(x).val();}),
        });
      },
    },
    'serverSide': true,
    'pageLength': 300,
    'columns': [
      {'data': 'status',
       'render': function(data, type, full, meta) {
         var statusClass = '';
         if (data == 'overdue') {
           statusClass = 'danger';
         } else if (data == 'reported') {
           statusClass = 'success';
         } else if (data == 'reported') {
           statusClass = 'success';
         } else {
           statusClass = 'info';
         }
         return '<span class="label label-' +
           statusClass + '">' + data + '</span>';
       },
      },
      {'data': 'registry_id',
       'render': function(data, type, full, meta) {
         return '<a href="'+full['publication_url']+'">'+
           full['registry_id']+'</a>';
       },
      },
      {'data': 'title'},
      {'data': 'completion_date'},
    ],
  });
  $('.status_filter').on('change', function() {
    table.draw();
    params = getTrialParams();
    params['status'] = $.map($('.status_filter:checked'), function(x) {
      return $(x).val();
    });
    window.history.pushState('status', '', '?' + $.param(params, true));
  });

}
