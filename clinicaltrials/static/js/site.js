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
    $('.status_filter').prop('checked', false).bootstrapToggle('off');
    $.each(params['status'], function(i, d) {
      $('.status_filter[value="'+d+'"]').prop('checked', true).bootstrapToggle('on');
    });
  }
}

function setCsvLinkAndTableDecoration(viewName) {
  return function(settings) {
    var api = this.api();
    var currentParams = JSON.parse(JSON.stringify(api.ajax.params()));
    currentParams.format = 'csv';
    // remove 'length' so we can download everything, unpaginated
    delete currentParams.length;
    $('#download').attr('href', '/api/' + viewName + '.csv?' + $.param(currentParams));
    var hasPages = api.page.info().pages > 1;
    var wrapper = $(this).closest('.dataTables_wrapper');
    var filter = wrapper.find('.dataTables_filter');
    filter.toggle(Boolean(filter.find('input').val() || hasPages));
    var pagination = wrapper.find('.dataTables_paginate');
    pagination.toggle(hasPages);
    var length = wrapper.find('.dataTables_length');
    length.toggle(hasPages);
    var info = wrapper.find('.dataTables_info');
    info.toggle(hasPages);
  };
}

function resizeCards() {
  // find the widest text; OR. the smallest font size!
  // find the largest font size that won't overflow the container
  // apply that to all the boxes
  var fontSize = 14;
  var largestHeight = 19;
  if ($(window).width() >= 768) {
    $('#summary-cards .header').css('height', 'auto');
    var maxFontSize = 150;
    var minFontSize = 10;
    var smallestFont = maxFontSize;
    var sizes = $.each($('#summary-cards .content'), function(i, container) {
      container = $(container);
      var data = BigText.calculateSizes(
        container, container.find('.big-text'), container.width(), maxFontSize, minFontSize);
      if(data.fontSizes[0] < smallestFont) {
        smallestFont = data.fontSizes[0];
      }
    });
    fontSize = smallestFont;
    $('#summary-cards .big-text').css('font-size', fontSize + 'px');
    var sizes = $.each($('#summary-cards .header'), function(i, container) {
      container = $(container);
      var h = container.height();
      if (h > largestHeight) {
        largestHeight = h;
      }
    });
    $('#summary-cards .header').height(largestHeight + 'px');
  } else {
    $('#summary-cards .big-text').css('font-size', fontSize + 'px');
    $('#summary-cards .header').height(largestHeight + 'px');
  }
}

function waitForEl(selector, callback) {
  if ($(selector).length) {
    callback();
  } else {
    setTimeout(function() {
      waitForEl(selector, callback);
    }, 100);
  }
};

function showPerformance(sponsorSlug) {
  var params = getTrialParams();
  if(typeof sponsorSlug !== 'undefined' && sponsorSlug !== '') {
    params['sponsor'] = sponsorSlug;
  }
  $.get('/api/performance/', params, function(d) {
    $('#num').text(d['reported']);
    $('#denom').text(d['due']);
    if (d['due']) {
      var percentage = (d['reported']/d['due'] * 100).toFixed(1);
      $('#percent-amount').text(percentage + '%');
    }
    $('#fine-amount').text(d['fines_str']);
    waitForEl('html.wf-active', resizeCards);
    $(window).resize(function() {
      resizeCards();
    });

    $('#summary-cards').fadeTo(1000, 1);
  });
}

function rankingTable(latestDate) {
  var url = '/api/rankings/?limit=5000';
  var params = getRankingParams();
  params['date'] = latestDate;
  params['due__gte'] = 1;
  setFormValues(params);
  var table = $('#sponsor_table').DataTable( {
    "dom": '<"datatable-top"fi>rt<"bottom"lp><"clear">',
    'drawCallback': setCsvLinkAndTableDecoration('rankings'),
    "order": [[ 3, 'asc' ], [ 0, 'asc' ]],
    "language": {
      "infoFiltered": '',
      "search": "",
      "searchPlaceholder": "Search sponsors"
    },
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
      {'name': 'sponsor__name', 'data': 'sponsor_name',
       'render': function(data, type, full, meta) {
         return '<a href="/sponsor/'+full['sponsor_slug']+'">'+
           full['sponsor_name']+'</a>';
       },
      },
      {'data': 'due', 'name': 'due'},
      {'data': 'reported', 'name': 'reported'},
      {'data': 'percentage', 'name': 'percentage',
       'render': function(data, type, full, meta) {
         return data + '%';
       },
      },
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
  var columnDefs = [];
  if(typeof sponsor_slug !== 'undefined' && sponsor_slug !== '') {
    params['sponsor'] = sponsor_slug;
    columnDefs = [{className: 'sponsor-col', targets: [1]}];
  }
  setFormValues(params);
  var table = $('#trials_table').DataTable( {
    'initComplete': function(settings, json) {
      $('#results').fadeTo(500, 1);
    },
    "dom": '<"datatable-top"fi>rt<"bottom"lp><"clear">',
    'drawCallback': setCsvLinkAndTableDecoration('trials'),
    'columnDefs': columnDefs,
    "language": {
      "infoFiltered": '',
      "search": "",
      "searchPlaceholder": "Search"
    },
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
      {'data': 'status', 'name': 'status',
       'render': function(data, type, full, meta) {
         var statusClass = '';
         if (data == 'overdue') {
           statusClass = 'danger';
         } else if (data == 'reported') {
           statusClass = 'success';
         } else if (data == 'reported-late') {
           statusClass = 'warning';
         } else {
           statusClass = 'info';
         }
         return '<span class="label label-' +
           statusClass + '">' + data + '</span>';
       },
      },
      {'name': 'sponsor__name', 'data': 'sponsor_name',
       'render': function(data, type, full, meta) {
         return '<a href="/sponsor/'+full['sponsor_slug']+'">'+
           full['sponsor_name']+'</a>';
       },
      },
      {'data': 'registry_id', 'name': 'registry_id',
       'render': function(data, type, full, meta) {
         return '<a href="/trial/'+full['registry_id']+'">'+
           full['registry_id']+'</a>';
       },
      },
      {'data': 'title', 'name': 'title',
       'render': function(data, type, full, meta) {
         var title = full['title'];
         if (full['is_pact']) {
           title += ' <span class="pact">[pACT]</span>';
         }
         return title;
       },
      },
      {'data': 'completion_date', 'name': 'completion_date'},
      {'data': 'days_late', 'name': 'days_late'},
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
    table.draw();
  });
}
