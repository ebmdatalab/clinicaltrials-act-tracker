function getQueryVariable(variable) {
  var query = window.location.search.substring(1);
  var vars = query.split('&');
  for (var i=0; i<vars.length; i++) {
    var pair = vars[i].split('=');
    if (pair[0] == variable) {
      if (typeof pair[1] === 'undefined') {
        return true
      } else {
        return pair[1];
      }
    }
  }
  return (false);
}

function rankingTable() {
  var url = '/api/rankings/?limit=5000';
  if (!getQueryVariable('all')) {
    url += '&sponsor__major=true';
  }
  $('#sponsor_table').DataTable( {
    'ajax': {
      'url': url,
      'dataSrc': 'results',
    },
    'serverSide': true,
    'columns': [
      {'data': 'rank'},
      {'data': 'sponsor',
       'render': function(data, type, full, meta) {
         return '<a href="/sponsor/'+full['sponsor_slug']+'">'+
           full['sponsor_name']+'</a>';
       },
      },
      {'data': 'due'},
      {'data': 'reported'},
      {'data': 'percentage'},
    ],
  });
}


function trialsTable(sponsor_slug) {
  var url = '/api/trials/?limit=5000&sponsor=' + sponsor_slug;
  $('#trials_table').DataTable( {
    'ajax': {
      'url': url,
      'dataSrc': 'results',
    },
    'serverSide': true,
    'columns': [
      {'data': 'status'}, // XXX
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
}
