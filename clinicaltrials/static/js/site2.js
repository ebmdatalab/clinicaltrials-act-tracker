function getQueryVariable(variable, coerceArray) {
  var query = window.location.search.substring(1);
  var vars = query.split('&');
  var vals = [];
  for (var i=0; i<vars.length; i++) {
    var pair = vars[i].split('=');
    var decoded = decodeURIComponent(pair[0]);
    if (decoded == variable) {
      vals.push(pair[1]);
    } else if (decoded == variable + '[]') {
      vals.push(pair[1]);
    }
  }
  if (!coerceArray && vals.length == 1) {
    return vals[0];
  } else {
    return vals;
  }

}


function setFormValues(params) {
  $('#total__gte').val(params['min_total']);
  if (params['is_industry_sponsor']) {
    $('.sponsor_type[value="'+params['is_industry_sponsor']+'"]').prop('checked', true);
  }
  if (params['status']) {
    $('.status_filter').prop('checked', false);
    $.each(params['status'], function(i, d) {
      $('.status_filter[value="'+d+'"]').prop('checked', true);
    });
  }
}

function setCsvLink(viewName) {
  return function(settings) {
    var api = this.api();
    // clone
    var currentParams = JSON.parse(JSON.stringify(api.ajax.params()));
    currentParams.format = 'csv';
    // remove 'length' so we can download everything, unpaginated
    delete currentParams.length;
    $('#download').attr('href', '/api/' + viewName + '.csv?' + $.param(currentParams));
  };
}

function rankingTable(latestDate) {
  var url = '/api/rankings/?limit=5000';
  var params = getRankingParams();
  params['date'] = latestDate;
  params['due__gte'] = 1;
  setFormValues(params);
  var table = $('#sponsor_table').DataTable( {
    "dom": 'f<"top"i>rt<"bottom"lp><"clear">',
    'drawCallback': setCsvLink('rankings'),
    "order": [[ 1, 'asc' ], [ 0, 'asc' ]],
    'ajax': {
      'url': url,
      'dataSrc': 'results',
      'data': function(d) {
        return $.extend(d, params, {
          'total__gte': $('#total__gte').val(),
          'with_trials_due': $('.overdue_type:checked').val(),
          'sponsor__is_industry_sponsor': $('.sponsor_type:checked').val(),
        });
      },
    },
    'pageLength': 100,
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
    params['min_total'] = $('#total__gte').val();
    window.history.pushState('min_total', params, '?' + $.param(params));
  });
  $('.sponsor_type').on('change', function() {
    table.draw();
    params['is_industry_sponsor'] = $('.sponsor_type:checked').val();
    window.history.pushState('industry_sponsor', params, '?' + $.param(params));
  });
  $('.overdue_type').on('change', function() {
    table.draw();
    params['with_trials_due'] = $('.with_trials_due:checked').val();
    window.history.pushState('with_trials_due', params, '?' + $.param(params));
  });
  $(window).bind('popstate', function () {
    var params = getRankingParams();
    setFormValues(params);
    table.draw();
  });
}

function getRankingParams() {
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
  var status = getQueryVariable('status', true);
  var params = {
    'status': status,
  };
  return params;
}

function trialsTable(sponsor_slug) {
  var url = '/api/trials/';
  var params = getTrialParams();
  if(typeof sponsor_slug !== 'undefined') {
    params['sponsor'] = sponsor_slug;
  }
  setFormValues(params);
  var table = $('#trials_table').DataTable( {
    "dom": 'f<"top"i>rt<"bottom"lp><"clear">',
    'drawCallback': setCsvLink('trials'),
    'ajax': {
      'url': url,
      'dataSrc': 'results',
      'data': function(d) {
        var adjusted = $.extend(d, params, {
          'status': $.map(
            $('.status_filter:checked'), function(x) {
              return $(x).val();
            }),
        });
        return adjusted;
      },
    },
    'serverSide': true,
    'pageLength': 100,
    "order": [[ 3, 'asc' ]],
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
      {'data': 'title',
       'render': function(data, type, full, meta) {
         var title = full['title'];
         if (full['is_pact']) {
           title += ' <span class="pact">[pACT]</span>';
         }
         return title;
       },
      },
      {'data': 'completion_date'},
    ],
  });
  $('.status_filter').on('change', function() {
    table.draw();
    params['status'] = $.map($('.status_filter:checked'), function(x) {
      return $(x).val();
    });
    window.history.pushState('status', params, '?' + $.param(params));
  });
  $(window).bind('popstate', function () {
    var params = getTrialParams();
    setFormValues(params);
    debugger
    table.draw();
  });

}
